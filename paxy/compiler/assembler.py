# paxy/assembler.py

import os
import sys
from typing import Union, Any

from bytecode import Bytecode, Instr, Label, CompilerFlags
from paxy.compiler.ir import (
    ParsedItem,
    FuncDef,
    ReturnMarker,
    Ident,
    LabelDecl,
    JumpRef,
    NamedJump,
    RangeBlock,
    ReturnMarker,
    COND_JUMP_OPS,
    UNCOND_JUMP_FIXED,
)
from paxy.compiler.twelve import (
    normalize_push_null_for_calls_312_seq,
    try_func_to_code_with_endfor_fix,
)


# What the resolver returns (only real bytecode items)
ResolvedItem = Union[Instr, Label]
# Internal placeholder tuple type (tagged unions used in the first pass)
Placeholder = tuple[Any, ...]


def _lg(name: str) -> tuple[bool, str]:
    if sys.version_info >= (3, 13):
        return (True, name)
    return (False, name)


class Assembler:
    """Resolves placeholders (labels and named jumps) into real bytecode items,
    and lowers function placeholders into LOAD_CONST/MAKE_FUNCTION/STORE_NAME.
    """

    # Placeholder tags
    TAG_JUMP = "__JUMP__"  # ("__JUMP__", JumpRef)
    TAG_CJUMP = "__CJUMP__"  # ("__CJUMP__", opcode, JumpRef)
    TAG_UJUMP = "__UJUMP__"  # ("__UJUMP__", opcode, JumpRef)
    TAG_NJUMP = "__NJUMP__"  # ("__NJUMP__", opcode, JumpRef)

    def __init__(self, items: list[ParsedItem], *, in_function: bool = False) -> None:
        self.items: list[ParsedItem] = items
        self._in_function: bool = in_function

        # discovery
        self._label_positions: dict[str, int] = {}
        self._label_objects: dict[str, Label] = {}

        # first pass (rewritten stream)
        self._resolved_stream: list[
            Union[Instr, Label, Placeholder, FuncDef, ReturnMarker]
        ] = []
        self._decl_idx_to_resolved_idx: dict[int, int] = {}

        # second pass (label/jump-patched stream)
        self._patched: list[Union[Instr, Label, FuncDef, ReturnMarker]] = []

        # final result (Instr/Label only)
        self._final: list[ResolvedItem] = []

        # name -> index in resolved stream where concrete Label lives
        self._name_to_resolved_index: dict[str, int] = {}

    # ---------- Public API ----------

    def resolve(self) -> list[ResolvedItem]:
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
                    raise SyntaxError(f"Duplicate LBL '{it.label_name}'")
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
          - GO (JumpRef) -> ("__JUMP__", JumpRef)
          - Native jumps with string targets -> ("__C/U/NJUMP__", opcode, JumpRef)
          - FuncDef / ReturnMarker are passed through for a later lowering pass
          - Other Instrs are kept as-is.
        """
        resolved: list[Union[Instr, Label, Placeholder, FuncDef, ReturnMarker]] = []
        decl_map: dict[int, int] = {}

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
                # Lower RNG var start end ... RNE into concrete loop skeleton,
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
        self._normalize_push_null_for_calls_312()
        self._decl_idx_to_resolved_idx = decl_map

    # ---------- Pass 1d: Build name -> resolved index map ----------

    def _index_label_decls(self) -> None:
        """Map label names to their position in the resolved stream (where Label() lives)."""
        name_to_resolved_index: dict[str, int] = {}
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
        patched: list[Union[Instr, Label, FuncDef, ReturnMarker]] = []
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

    def _lower_funcdef(self, func: FuncDef) -> list[ResolvedItem]:
        # 1) Resolve body inside-function
        inner_resolved = Assembler(func.body, in_function=True).resolve()

        # 2) Rewrite locals/globals
        lowered_body = self._rewrite_locals_for_function(
            inner_resolved, list(func.params)
        )

        # 3) Sanitize mid-body RESUMEs and spurious default returns
        lowered_body = self._sanitize_function_body(lowered_body)

        # 4) Ensure *some* return exists (only if none at all after sanitize)
        has_any_return = any(
            isinstance(ins, Instr) and ins.name == "RETURN_VALUE"
            for ins in lowered_body
        )
        if not has_any_return:
            lowered_body.extend(
                [
                    Instr("LOAD_CONST", 0, lineno=func.lineno),
                    Instr("RETURN_VALUE", lineno=func.lineno),
                ]
            )

        # 5) (optional) debug
        if os.getenv("PAXY_DEBUG") == "1":
            print(f"== FUNC {func.name} AFTER REWRITE ==")
            for i, ins in enumerate(lowered_body):
                print(f"{i:03d}: {ins!r}")

        # 6) Build code object FROM lowered_body
        bc_func = Bytecode(lowered_body)
        bc_func.argcount = len(func.params)
        bc_func.argnames = list(func.params)
        bc_func.flags |= (
            CompilerFlags.OPTIMIZED | CompilerFlags.NEWLOCALS | CompilerFlags.NOFREE
        )
        bc_func.first_lineno = func.lineno

        if sys.version_info >= (3, 13):
            maker = Instr("MAKE_FUNCTION", lineno=func.lineno)
            func_code = bc_func.to_code()
        else:
            maker = Instr("MAKE_FUNCTION", 0, lineno=func.lineno)
            func_code = try_func_to_code_with_endfor_fix(bc_func)

        # 7) Emit loader sequence
        return [
            Instr("LOAD_CONST", func_code, lineno=func.lineno),
            maker,
            Instr("STORE_NAME", func.name, lineno=func.lineno),
        ]

    # ---------- Pass 3: Lower functions and returns ----------

    def _rewrite_locals_for_function(
        self,
        lowered_body: list[ResolvedItem],
        params: list[str],
    ) -> list[ResolvedItem]:
        """
        Convert NAME ops to FAST for locals (params + anything stored/deleted),
        and LOAD_NAME(non-local) -> LOAD_GLOBAL with 3.13 bitflag tuple.
        Also normalize Ident args to str for all FAST ops.
        """
        # 1) discover locals
        local_names: set[str] = set(params)
        for ins in lowered_body:
            if isinstance(ins, Instr):
                nm = ins.name
                arg = ins.arg
                if nm in ("STORE_NAME", "DELETE_NAME", "STORE_FAST", "DELETE_FAST"):
                    if isinstance(arg, (str, Ident)):
                        local_names.add(self._as_name(arg))

        # 2) rewrite
        out: list[ResolvedItem] = []
        for ins in lowered_body:
            if not isinstance(ins, Instr):
                out.append(ins)
                continue

            nm = ins.name
            arg = ins.arg

            if isinstance(arg, (str, Ident)):
                name = self._as_name(arg)

                if nm == "LOAD_NAME":
                    if name in local_names:
                        out.append(Instr("LOAD_FAST", name, lineno=ins.lineno))
                    else:
                        # CPython 3.13: LOAD_GLOBAL requires (bool, name) tuple
                        out.append(Instr("LOAD_GLOBAL", _lg(name), lineno=ins.lineno))
                    continue

                if nm == "STORE_NAME":
                    out.append(Instr("STORE_FAST", name, lineno=ins.lineno))
                    continue

                if nm == "DELETE_NAME":
                    out.append(Instr("DELETE_FAST", name, lineno=ins.lineno))
                    continue

                if nm in ("LOAD_FAST", "STORE_FAST", "DELETE_FAST"):
                    out.append(Instr(nm, name, lineno=ins.lineno))
                    continue

            # default: pass through unchanged
            out.append(ins)

        # 3) sanity in optimized functions: no *_NAME left
        leftovers = [
            (i, ins.name, ins.arg, getattr(ins, "lineno", None))
            for i, ins in enumerate(out)
            if isinstance(ins, Instr) and ins.name.endswith("_NAME")
        ]
        if leftovers:
            details = ", ".join(
                f"{idx}:{nm}:{arg}@{ln}" for idx, nm, arg, ln in leftovers
            )
            raise RuntimeError(
                f"internal: NAME ops remain in optimized function after rewrite: {details}"
            )
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
                out.append(Instr("LOAD_GLOBAL", _lg(ins.arg), lineno=ins.lineno))
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
        final: list[ResolvedItem] = []
        for entry in self._patched:
            if isinstance(entry, FuncDef):
                final.extend(self._lower_funcdef(entry))

            elif isinstance(entry, ReturnMarker):
                if not self._in_function:
                    # RET outside of function/subroutine is invalid
                    raise SyntaxError("RET outside of SUB")
                # Lower to real return
                if entry.has_value:
                    final.append(Instr("RETURN_VALUE", lineno=entry.lineno))
                else:
                    final.extend(
                        [
                            Instr("LOAD_CONST", 0, lineno=entry.lineno),
                            Instr("RETURN_VALUE", lineno=entry.lineno),
                        ]
                    )

            else:
                # Instr or Label
                final.append(entry)

        self._final = final

    # ---------- Helpers ----------

    def _as_name(self, arg: object) -> str:
        """Return identifier name as a plain str (accept Ident or str)."""
        if isinstance(arg, Ident):
            return str(arg)
        if isinstance(arg, str):
            return arg
        return str(arg)

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
            raise SyntaxError(f"GO to undefined LBL '{name}'")
        return idx

    def _ensure_target_defined(self, name: str) -> None:
        if name not in self._name_to_resolved_index:
            raise SyntaxError(f"jump to undefined LBL '{name}'")

    def _emit_token_load_instrs(self, tok: object, lineno: int) -> list[Instr]:
        """
        Helper: load a parsed token either as a local/global name or a constant.
        If we're compiling inside a function (optimized frame), prefer FAST for identifiers.
        """
        if isinstance(tok, Ident):
            name = str(tok)
            if self._in_function:
                return [Instr("LOAD_FAST", name, lineno=lineno)]
            return [Instr("LOAD_NAME", name, lineno=lineno)]
        return [Instr("LOAD_CONST", tok, lineno=lineno)]

    def _lower_rangeblock_to_stream(self, it: RangeBlock) -> list[ResolvedItem]:
        """
            RNG <var> <start> <end> [<step>]
            <body>
            RNE
            -->
            PUSH_NULL
            LOAD_GLOBAL range
            <load args>
            CALL nargs
            GET_ITER
        loop:
            FOR_ITER end
            STORE_NAME <var>
            <body without per-line bookends/sentinels>
            JUMP_BACKWARD loop
        end:
            END_FOR
            POP_TOP
        """
        out: list[ResolvedItem] = []

        # 1) Build iter(range(...))
        out.append(Instr("PUSH_NULL", lineno=it.lineno))
        out.append(Instr("LOAD_GLOBAL", _lg("range"), lineno=it.lineno))

        # Collect start/end[/step]
        args: list[object] = [it.start, it.end]
        step = getattr(it, "step", None)
        if step is not None:
            args.append(step)

        for tok in args:
            out.extend(self._emit_token_load_instrs(tok, it.lineno))

        out.append(Instr("CALL", len(args), lineno=it.lineno))
        out.append(Instr("GET_ITER", lineno=it.lineno))

        # 2) Loop skeleton
        l_loop = Label()
        l_end = Label()
        out.append(l_loop)
        out.append(Instr("FOR_ITER", l_end, lineno=it.lineno))
        out.append(Instr("STORE_NAME", it.var, lineno=it.lineno))

        # 3) Splice body, dropping line bookends and the sentinel LOAD_CONST 0
        DROP_NAMES = {"RESUME", "RETURN_VALUE", "RETURN_CONST"}
        for ins in it.body:
            if isinstance(ins, Instr):
                if ins.name in DROP_NAMES:
                    continue
                # Filter the sentinel that precedes implicit returns in single-line lowering
                if ins.name == "LOAD_CONST" and ins.arg == 0:
                    continue
            out.append(ins)

        out.append(Instr("JUMP_BACKWARD", l_loop, lineno=it.lineno))

        # 4) Loop end + cleanup (tests want POP_TOP present)
        out.append(l_end)
        out.append(Instr("END_FOR", lineno=it.lineno))
        # if sys.version_info >= (3, 13):
        out.append(Instr("POP_TOP", lineno=it.lineno))

        return out

    def _sanitize_function_body(self, body: list[ResolvedItem]) -> list[ResolvedItem]:
        """Remove mid-body RESUMEs and default RETURN_CONST if there is an explicit return."""
        # Keep only the first RESUME
        saw_resume = False
        tmp: list[ResolvedItem] = []
        for ins in body:
            if isinstance(ins, Instr) and ins.name == "RESUME":
                if saw_resume:
                    continue
                saw_resume = True
                tmp.append(ins)
            else:
                tmp.append(ins)

        # # If there is any explicit RETURN_VALUE, remove all RETURN_CONST
        # has_explicit_return = any(
        #     isinstance(ins, Instr) and ins.name == "RETURN_VALUE" for ins in tmp
        # )
        # if has_explicit_return:
        #     tmp = [
        #         ins
        #         for ins in tmp
        #         if not (isinstance(ins, Instr) and ins.name == "RETURN_CONST")
        #     ]

        return tmp

    def _normalize_push_null_for_calls_312(self) -> None:
        """On Py 3.12 only, make sure PUSH_NULL is *under* the callable."""
        self._resolved_stream = normalize_push_null_for_calls_312_seq(
            self._resolved_stream
        )
