# paxy/assembler.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Tuple, Union, Any
from types import CodeType
import dis as _dis

from bytecode import Bytecode, Instr, Label, CompilerFlags
from paxy.parser import Parser
from paxy.constants import COND_JUMP_OPS, UNCOND_JUMP_FIXED
from paxy.ir import (
    ParsedItem,
    FuncDef,
    ReturnMarker,
    Ident,
    LabelDecl,
    JumpRef,
    NamedJump,
    RangeBlock,
)


# What the resolver returns (only real bytecode items)
ResolvedItem = Union[Instr, Label]
# Internal placeholder tuple type (tagged unions used in the first pass)
Placeholder = Tuple[Any, ...]


class Assembler:
    """Resolves placeholders (labels and named jumps) into real bytecode items,
    and lowers function placeholders into LOAD_CONST/MAKE_FUNCTION/STORE_NAME.
    """

    # Placeholder tags
    TAG_JUMP = "__JUMP__"  # ("__JUMP__", JumpRef)
    TAG_CJUMP = "__CJUMP__"  # ("__CJUMP__", opcode, JumpRef)
    TAG_UJUMP = "__UJUMP__"  # ("__UJUMP__", opcode, JumpRef)
    TAG_NJUMP = "__NJUMP__"  # ("__NJUMP__", opcode, JumpRef)

    def __init__(self, items: List[ParsedItem], *, in_function: bool = False) -> None:
        self.items: List[ParsedItem] = items
        self._in_function: bool = in_function

        # discovery
        self._label_positions: Dict[str, int] = {}
        self._label_objects: Dict[str, Label] = {}

        # first pass (rewritten stream)
        self._resolved_stream: List[
            Union[Instr, Label, Placeholder, FuncDef, ReturnMarker]
        ] = []
        self._decl_idx_to_resolved_idx: Dict[int, int] = {}

        # second pass (label/jump-patched stream)
        self._patched: List[Union[Instr, Label, FuncDef, ReturnMarker]] = []

        # final result (Instr/Label only)
        self._final: List[ResolvedItem] = []

        # name -> index in resolved stream where concrete Label lives
        self._name_to_resolved_index: Dict[str, int] = {}

    # ---------- Public API ----------

    def resolve(self) -> List[ResolvedItem]:
        """Run all passes and return a stream of Instr/Label only."""
        self._discover_declared_labels()
        self._build_label_objects()
        self._first_pass_rewrite()
        self._index_label_decls()
        self._second_pass_patch_jumps()
        self._lower_functions_and_returns()
        self._sanity_check()
        return self._final

    # ---------- Pass 1a: Discover labels ----------

    def _discover_declared_labels(self) -> None:
        """Scan the original items and record label declaration positions."""
        for idx, it in enumerate(self.items):
            if isinstance(it, LabelDecl):
                if it.label_name in self._label_positions:
                    raise SyntaxError(f"Duplicate LABEL '{it.label_name}'")
                self._label_positions[it.label_name] = idx

    # ---------- Pass 1b: Create Label objects ----------

    def _build_label_objects(self) -> None:
        """Create concrete bytecode.Label objects for every declared name."""
        self._label_objects = {name: Label() for name in self._label_positions}

    # ---------- Pass 1c: Rewrite stream to placeholders ----------

    def _first_pass_rewrite(self) -> None:
        """
        Build a temporary stream where:
          - LabelDecl -> Label()
          - GOTO (JumpRef) -> ("__JUMP__", JumpRef)
          - Native jumps with string targets -> ("__C/U/NJUMP__", opcode, JumpRef)
          - FuncDef / ReturnMarker are passed through for a later lowering pass
          - Other Instrs are kept as-is.
        """
        resolved: List[Union[Instr, Label, Placeholder, FuncDef, ReturnMarker]] = []
        decl_map: Dict[int, int] = {}

        for idx, it in enumerate(self.items):
            if isinstance(it, LabelDecl):
                lbl = self._label_objects[it.label_name]
                decl_map[idx] = len(resolved)
                resolved.append(lbl)

            elif isinstance(it, JumpRef):
                resolved.append((self.TAG_JUMP, it))

            elif isinstance(it, NamedJump):
                # Defer to pass 2—convert to real Instr with Label later
                resolved.append(
                    (self.TAG_NJUMP, it.opcode, JumpRef(it.target_name, it.lineno))
                )

            elif isinstance(it, RangeBlock):
                # Lower RANGE var start end ... RANGEEND into concrete loop skeleton,
                # leaving the body items raw so later passes can still process them.
                # range(start, end)
                resolved.extend(self._lower_rangeblock_to_stream(it))

            elif isinstance(it, FuncDef) or isinstance(it, ReturnMarker):
                # Leave function placeholders and returns for a later lowering stage
                resolved.append(it)

            elif isinstance(it, Instr) and isinstance(it.name, str):
                op = it.name
                arg = it.arg
                if op in COND_JUMP_OPS and isinstance(arg, (str, Ident)):
                    resolved.append((self.TAG_CJUMP, op, JumpRef(str(arg), it.lineno)))
                elif op in UNCOND_JUMP_FIXED and isinstance(arg, (str, Ident)):
                    resolved.append((self.TAG_UJUMP, op, JumpRef(str(arg), it.lineno)))
                else:
                    resolved.append(it)

            else:
                resolved.append(it)

        self._resolved_stream = resolved
        self._decl_idx_to_resolved_idx = decl_map

    # ---------- Pass 1d: Build name -> resolved index map ----------

    def _index_label_decls(self) -> None:
        """Map label names to their position in the resolved stream (where Label() lives)."""
        name_to_resolved_index: Dict[str, int] = {}
        for decl_idx, res_idx in self._decl_idx_to_resolved_idx.items():
            ld = self.items[decl_idx]
            if not isinstance(ld, LabelDecl):
                # Internal invariant
                raise RuntimeError(
                    "internal error: decl index did not point to LabelDecl"
                )
            name_to_resolved_index[ld.label_name] = res_idx
        self._name_to_resolved_index = name_to_resolved_index

    # ---------- Pass 2: Patch label-related placeholders to real Instrs ----------

    def _second_pass_patch_jumps(self) -> None:
        patched: List[Union[Instr, Label, FuncDef, ReturnMarker]] = []
        for pos, entry in enumerate(self._resolved_stream):
            if isinstance(entry, tuple):
                tag = entry[0]
                if tag == self.TAG_JUMP:
                    _, ref = entry
                    patched.append(self._make_resolved_uncond_jump(pos, ref))
                elif tag == self.TAG_CJUMP:
                    _, opcode, ref = entry
                    patched.append(self._make_resolved_fixed_jump(opcode, ref))
                elif tag == self.TAG_UJUMP:
                    _, opcode, ref = entry
                    patched.append(self._make_resolved_fixed_jump(opcode, ref))
                elif tag == self.TAG_NJUMP:
                    _, opcode, ref = entry
                    patched.append(self._make_resolved_fixed_jump(opcode, ref))
                else:
                    raise RuntimeError(f"unknown placeholder {tag!r}")
            else:
                patched.append(entry)

        self._patched = patched

    def _make_resolved_uncond_jump(self, pos: int, ref: JumpRef) -> Instr:
        target_idx = self._lookup_target_index(ref.target_name)
        opcode = "JUMP_FORWARD" if target_idx > pos else "JUMP_BACKWARD"
        return Instr(opcode, self._label_objects[ref.target_name], lineno=ref.lineno)

    def _make_resolved_fixed_jump(self, opcode: str, ref: JumpRef) -> Instr:
        self._ensure_target_defined(ref.target_name)
        return Instr(opcode, self._label_objects[ref.target_name], lineno=ref.lineno)

    def _lower_funcdef(self, func: FuncDef) -> List[ResolvedItem]:
        """
        Lower a FuncDef placeholder into:
        LOAD_CONST <code>
        MAKE_FUNCTION
        STORE_NAME <name>

        For zero-arg SUBs (subroutines), we rewrite all name ops to GLOBALs.
        For functions with params, we rewrite params + assigned names to FAST locals,
        and other name loads to GLOBALS.
        """
        # Resolve function body (inside-function mode so RETURN markers lower correctly)
        inner_resolved = Assembler(func.body, in_function=True).resolve()

        lowered_body: List[ResolvedItem] = list(inner_resolved)

        for it in func.body:
            if isinstance(it, RangeBlock):
                lowered_body.extend(self._lower_rangeblock_to_stream(it))
            else:
                lowered_body.append(it)

        # Ensure a return if author omitted
        if not lowered_body or str(getattr(lowered_body[-1], "name", "")) not in {
            "RETURN_CONST",
            "RETURN_VALUE",
        }:
            lowered_body.append(Instr("RETURN_CONST", 0, lineno=func.lineno))

        # Choose rewrite mode
        global_mode = len(func.params) == 0
        if global_mode:
            lowered_body = self._rewrite_names_global_mode(lowered_body)
        else:
            lowered_body = self._rewrite_locals_for_function(
                lowered_body, list(func.params)
            )

        # Build function code
        bc = Bytecode(lowered_body)
        bc.name = func.name
        bc.argcount = len(func.params)  # ← CRITICAL: set argcount
        bc.argnames = list(func.params)  # names for those args
        # Optimized function frame is fine; STORE_GLOBAL/LOAD_GLOBAL work with it
        bc.flags |= (
            CompilerFlags.NOFREE | CompilerFlags.OPTIMIZED | CompilerFlags.NEWLOCALS
        )

        first = next((x for x in lowered_body if isinstance(x, Instr)), None)
        if first is not None and first.lineno:
            bc.first_lineno = first.lineno

        codeobj = bc.to_code()

        return [
            Instr("LOAD_CONST", codeobj, lineno=func.lineno),
            Instr("MAKE_FUNCTION", lineno=func.lineno),  # 3.13: no arg
            Instr("STORE_NAME", func.name, lineno=func.lineno),
        ]

    # ---------- Pass 3: Lower functions and returns ----------

    def _rewrite_locals_for_function(
        self,
        body: list[ResolvedItem],
        params: list[str],
    ) -> list[ResolvedItem]:
        """
        Local-mode: params are locals, and any STORE_NAME target becomes a local.
        Other reads fall back to LOAD_GLOBAL.
        """
        locals_set = set(params)
        for ins in body:
            if (
                isinstance(ins, Instr)
                and ins.name == "STORE_NAME"
                and isinstance(ins.arg, str)
            ):
                locals_set.add(ins.arg)

        out: list[ResolvedItem] = []
        for ins in body:
            if not isinstance(ins, Instr):
                out.append(ins)
                continue

            if ins.name == "STORE_NAME" and isinstance(ins.arg, str):
                if ins.arg in locals_set:
                    out.append(Instr("STORE_FAST", ins.arg, lineno=ins.lineno))
                else:
                    out.append(Instr("STORE_GLOBAL", ins.arg, lineno=ins.lineno))
            elif ins.name == "LOAD_NAME" and isinstance(ins.arg, str):
                if ins.arg in locals_set:
                    out.append(Instr("LOAD_FAST", ins.arg, lineno=ins.lineno))
                else:
                    out.append(Instr("LOAD_GLOBAL", ins.arg, lineno=ins.lineno))
            else:
                out.append(ins)

        return out

    def _rewrite_names_global_mode(
        self,
        body: list[ResolvedItem],
    ) -> list[ResolvedItem]:
        """
        Zero-arg SUBs behave like classic subroutines: assignments are global.
        Rewrite:
        STORE_NAME x -> STORE_GLOBAL x
        LOAD_NAME  x -> LOAD_GLOBAL x
        (Other ops unchanged.)
        """
        out: list[ResolvedItem] = []
        for ins in body:
            if not isinstance(ins, Instr):
                out.append(ins)
                continue

            if ins.name == "STORE_NAME" and isinstance(ins.arg, str):
                out.append(Instr("STORE_GLOBAL", ins.arg, lineno=ins.lineno))
            elif ins.name == "LOAD_NAME" and isinstance(ins.arg, str):
                out.append(Instr("LOAD_GLOBAL", ins.arg, lineno=ins.lineno))
            else:
                out.append(ins)

        return out

    def _lower_functions_and_returns(self) -> None:
        """
        Convert:
          - FuncDef -> LOAD_CONST(code); MAKE_FUNCTION; STORE_NAME <name>
          - ReturnMarker:
              * in module context -> error
              * in function context -> RETURN_VALUE or RETURN_CONST 0
        """
        final: List[ResolvedItem] = []
        for entry in self._patched:
            if isinstance(entry, FuncDef):
                final.extend(self._lower_funcdef(entry))

            elif isinstance(entry, ReturnMarker):
                if not self._in_function:
                    # RETURN outside of function/subroutine is invalid
                    raise SyntaxError("RETURN outside of SUB")
                # Lower to real return
                if entry.has_value:
                    final.append(Instr("RETURN_VALUE", lineno=entry.lineno))
                else:
                    final.append(Instr("RETURN_CONST", 0, lineno=entry.lineno))

            else:
                # Instr or Label
                final.append(entry)

        self._final = final

    # ---------- Helpers ----------

    def _sanity_check(self) -> None:
        """
        Final pass invariants:
          - No tuple placeholders remain.
          - Any jump op still present targets a real Label.
        """
        for obj in self._final:
            # Should never see placeholders in the final stream
            if isinstance(obj, tuple):
                raise RuntimeError(f"unresolved jump placeholder: {obj!r}")

            # For real instructions, verify jump args are Labels
            if isinstance(obj, Instr):
                if obj.name in (COND_JUMP_OPS | UNCOND_JUMP_FIXED):
                    from bytecode import Label as _Lbl

                    if not isinstance(obj.arg, _Lbl):
                        raise RuntimeError(f"jump still has non-Label arg: {obj!r}")

    def _lookup_target_index(self, name: str) -> int:
        idx = self._name_to_resolved_index.get(name)
        if idx is None:
            raise SyntaxError(f"GOTO to undefined LABEL '{name}'")
        return idx

    def _ensure_target_defined(self, name: str) -> None:
        if name not in self._name_to_resolved_index:
            raise SyntaxError(f"jump to undefined LABEL '{name}'")

    def _emit_token_load_instrs(self, tok: object, lineno: int) -> list[Instr]:
        """
        Helper: load a parsed token either as a name (Ident) or a constant.
        """
        if isinstance(tok, Ident):
            return [Instr("LOAD_NAME", str(tok), lineno=lineno)]
        else:
            return [Instr("LOAD_CONST", tok, lineno=lineno)]

    def _lower_rangeblock_to_stream(
        self, it: RangeBlock
    ) -> List[Union[Instr, Label, Placeholder, FuncDef, ReturnMarker]]:
        """
        Expand a RANGE block into concrete loop prologue/epilogue and recursively
        lower any nested RangeBlock in the body.
        """
        out: List[Union[Instr, Label, Placeholder, FuncDef, ReturnMarker]] = []
        # range(start, end)
        out.append(Instr("LOAD_GLOBAL", (True, "range"), lineno=it.lineno))
        out.extend(self._emit_token_load_instrs(it.start, it.lineno))
        out.extend(self._emit_token_load_instrs(it.end, it.lineno))
        out.append(Instr("CALL", 2, lineno=it.lineno))
        out.append(Instr("GET_ITER", lineno=it.lineno))

        l_loop = Label()
        l_end = Label()
        out.append(l_loop)
        out.append(Instr("FOR_ITER", l_end, lineno=it.lineno))
        out.append(Instr("STORE_NAME", it.var, lineno=it.lineno))

        # Body: recursively lower nested RangeBlocks; translate placeholders like pass 1c.
        for elt in it.body:
            if isinstance(elt, RangeBlock):
                out.extend(self._lower_rangeblock_to_stream(elt))
            elif isinstance(elt, NamedJump):
                out.append(
                    (self.TAG_NJUMP, elt.opcode, JumpRef(elt.target_name, elt.lineno))
                )
            elif isinstance(elt, JumpRef):
                out.append((self.TAG_JUMP, elt))
            elif isinstance(elt, LabelDecl):
                # Labels inside RANGE would need discovery before this pass.
                # For now, disallow to avoid unresolved labels.
                raise SyntaxError("LABEL inside RANGE block is not supported")
            else:
                # Instr / FuncDef / ReturnMarker — already allowed in 'out' type
                out.append(elt)

        out.append(Instr("JUMP_BACKWARD", l_loop, lineno=it.lineno))
        out.append(l_end)
        out.append(Instr("END_FOR", lineno=it.lineno))
        out.append(Instr("POP_TOP", lineno=it.lineno))
        return out


# ----------------------- Public entry point -----------------------


def assemble_file(src_path: Path) -> CodeType:
    """
    Parse .paxy -> (ParsedItem stream) -> resolve labels -> Bytecode -> CodeType
    """
    parser = Parser()
    parsed: List[ParsedItem] = parser.parse_file(src_path)

    resolved = Assembler(parsed).resolve()

    # Optional debug dump
    if os.getenv("PAXY_DEBUG") == "1":
        out: List[str] = []
        out.append("== RESOLVED ==")
        for i, obj in enumerate(resolved):
            out.append(f"{i:03d}: {obj!r}")
        bc_dbg = Bytecode(resolved)
        code_dbg = bc_dbg.to_code()
        out.append("== DISASSEMBLY ==")
        out.append(_dis.Bytecode(code_dbg).dis())  # returns a str in 3.13
        dbg_path = Path(os.getenv("PAXY_DEBUG_OUT", "/tmp/paxy_debug.txt"))
        dbg_path.write_text("\n".join(out))
        return code_dbg

    # Build final bytecode object
    bc = Bytecode(resolved)
    bc.filename = str(src_path)
    bc.name = "<module>"
    bc.flags |= CompilerFlags.NOFREE

    # First instruction lineno is used as first_lineno
    if resolved:
        first: Instr | None = next((x for x in resolved if isinstance(x, Instr)), None)
        if first is not None and first.lineno:
            bc.first_lineno = first.lineno

    code = bc.to_code()

    if os.getenv("PAXY_DEBUG") == "1":
        print("== DISASSEMBLY ==")
        _dis.dis(code)

    return code
