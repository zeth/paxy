# paxy/assembler.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Tuple, Union, Any
from types import CodeType
import dis as _dis

from bytecode import Bytecode, Instr, Label, CompilerFlags
from .parser import Parser
from .labels import LabelDecl, JumpRef, NamedJump
from .ident import Ident
from .constants import COND_JUMP_OPS, UNCOND_JUMP_FIXED

# What the parser can produce (no Label yet)
ParsedItem = Union[Instr, LabelDecl, JumpRef, NamedJump]
# What the resolver returns (only real bytecode items)
ResolvedItem = Union[Instr, Label]


def _resolve_labels(items: List[ParsedItem]) -> List[ResolvedItem]:
    """
    Replace LabelDecl with actual bytecode.Label instances and
    resolve all jump placeholders (BASIC GOTO + native jumps naming labels).
    """
    # 1) Find declared labels
    label_positions: Dict[str, int] = {}
    for idx, it in enumerate(items):
        if isinstance(it, LabelDecl):
            if it.label_name in label_positions:
                raise SyntaxError(f"Duplicate LABEL '{it.label_name}'")
            label_positions[it.label_name] = idx

    # 2) Create real bytecode.Label objects
    label_objects: Dict[str, Label] = {name: Label() for name in label_positions}

    # 3) First pass: rewrite stream to placeholders
    resolved: List[Union[Instr, Label, Tuple[Any, ...]]] = []
    decl_index_to_resolved_index: Dict[int, int] = {}

    for idx, it in enumerate(items):
        if isinstance(it, LabelDecl):
            lbl = label_objects[it.label_name]
            decl_index_to_resolved_index[idx] = len(resolved)
            resolved.append(lbl)

        elif isinstance(it, JumpRef):
            resolved.append(("__JUMP__", it))  # decide forward/backward later

        elif isinstance(it, NamedJump):
            resolved.append(
                ("__NJUMP__", it.opcode, JumpRef(it.target_name, it.lineno))
            )

        elif isinstance(it, Instr) and isinstance(it.name, str):
            op = it.name
            arg = it.arg

            if op in COND_JUMP_OPS and isinstance(arg, (str, Ident)):
                resolved.append(("__CJUMP__", op, JumpRef(str(arg), it.lineno)))
            elif op in UNCOND_JUMP_FIXED and isinstance(arg, (str, Ident)):
                resolved.append(("__UJUMP__", op, JumpRef(str(arg), it.lineno)))
            else:
                resolved.append(it)

        else:
            resolved.append(it)

    # 4) Map label declaration indices to resolved positions
    name_to_resolved_index: Dict[str, int] = {}
    for decl_idx, res_idx in decl_index_to_resolved_index.items():
        ld = items[decl_idx]
        if not isinstance(ld, LabelDecl):
            raise RuntimeError("internal error: decl index did not point to LabelDecl")
        name_to_resolved_index[ld.label_name] = res_idx

    # 5) Second pass: patch placeholders to real Instrs with Label args
    final: List[ResolvedItem] = []
    for pos, entry in enumerate(resolved):
        if isinstance(entry, tuple):
            tag = entry[0]

            if tag == "__JUMP__":
                _, ref = entry
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"GOTO to undefined LABEL '{ref.target_name}'")
                target_pos = name_to_resolved_index[ref.target_name]
                opcode = "JUMP_FORWARD" if target_pos > pos else "JUMP_BACKWARD"
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            elif tag == "__CJUMP__":
                _, opcode, ref = entry
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"jump to undefined LABEL '{ref.target_name}'")
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            elif tag == "__UJUMP__":
                _, opcode, ref = entry
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"jump to undefined LABEL '{ref.target_name}'")
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            elif tag == "__NJUMP__":
                _, opcode, ref = entry
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"jump to undefined LABEL '{ref.target_name}'")
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            else:
                raise RuntimeError(f"unknown placeholder {tag!r}")

        else:
            final.append(entry)

    # Sanity pass
    for obj in final:
        if isinstance(obj, tuple):
            raise RuntimeError(f"unresolved jump placeholder: {obj!r}")
        if isinstance(obj, Instr):
            if obj.name in COND_JUMP_OPS | UNCOND_JUMP_FIXED:
                from bytecode import Label as _Lbl

                if not isinstance(obj.arg, _Lbl):
                    raise RuntimeError(f"jump still has non-Label arg: {obj}")
    return final


def assemble_file(src_path: Path) -> CodeType:
    """
    Parse .paxy -> (ParsedItem stream) -> resolve labels -> Bytecode -> CodeType
    """
    parser = Parser()
    instrs: List[ParsedItem] = parser.parse_file(src_path)

    resolved = _resolve_labels(instrs)

    if os.getenv("PAXY_DEBUG") == "1":
        out: List[str] = []
        out.append("== RESOLVED ==")
        for i, obj in enumerate(resolved):
            out.append(f"{i:03d}: {obj!r}")
        bc = Bytecode(resolved)
        code = bc.to_code()
        out.append("== DISASSEMBLY ==")
        out.append(_dis.Bytecode(code).dis())  # returns a str in 3.13
        dbg_path = Path(os.getenv("PAXY_DEBUG_OUT", "/tmp/paxy_debug.txt"))
        dbg_path.write_text("\n".join(out))
        return code

    bc = Bytecode(resolved)
    bc.filename = str(src_path)
    bc.name = "<module>"
    bc.flags |= CompilerFlags.NOFREE

    if resolved:
        first: Instr | None = next((x for x in resolved if isinstance(x, Instr)), None)
        if first is not None and first.lineno:
            bc.first_lineno = first.lineno

    code = bc.to_code()

    if os.getenv("PAXY_DEBUG") == "1":
        print("== DISASSEMBLY ==")
        _dis.dis(code)

    return code
