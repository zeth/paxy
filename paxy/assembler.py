# paxy/assembler.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Tuple, Union, Any, cast
from types import CodeType
import dis as _dis

from bytecode import Bytecode, Instr, Label, CompilerFlags
from .parser import Parser
from .labels import LabelDecl, JumpRef, NamedJump
from .ident import Ident
from .constants import COND_JUMP_OPS, UNCOND_JUMP_FIXED


def _resolve_labels(items: List[Instr]) -> List[Union[Instr, Label]]:
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

    # 3) First pass: rewrite stream to:
    #    - replace LabelDecl with Label()
    #    - keep GOTO as ("__JUMP__", JumpRef)
    #    - rewrite native jumps with string/Ident targets to placeholders:
    #         ("__CJUMP__", OPCODE, JumpRef)  for conditional
    #         ("__UJUMP__", OPCODE, JumpRef)  for explicit-direction uncond
    #         ("__NJUMP__", OPCODE, JumpRef)  for named native jumps
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
            # Defer: patch to real Instr with Label after labels are created
            resolved.append(("__NJUMP__", it.opcode, JumpRef(it.target, it.lineno)))

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

    # 4) Map label declaration indices to their resolved positions
    name_to_resolved_index: Dict[str, int] = {}
    for decl_idx, res_idx in decl_index_to_resolved_index.items():
        it = items[decl_idx]
        if not isinstance(it, LabelDecl):
            raise RuntimeError("internal error: decl index did not point to LabelDecl")
        name_to_resolved_index[it.label_name] = res_idx

    # 5) Second pass: patch placeholders to real Instrs with Label args
    final: List[Union[Instr, Label]] = []
    for pos, it in enumerate(resolved):
        if isinstance(it, tuple):
            tag = it[0]

            if tag == "__JUMP__":
                _, ref = it
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"GOTO to undefined LABEL '{ref.target_name}'")
                target_pos = name_to_resolved_index[ref.target_name]
                opcode = "JUMP_FORWARD" if target_pos > pos else "JUMP_BACKWARD"
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            elif tag == "__CJUMP__":
                _, opcode, ref = it
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"jump to undefined LABEL '{ref.target_name}'")
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            elif tag == "__UJUMP__":
                _, opcode, ref = it
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"jump to undefined LABEL '{ref.target_name}'")
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            elif tag == "__NJUMP__":
                _, opcode, ref = it
                if ref.target_name not in name_to_resolved_index:
                    raise SyntaxError(f"jump to undefined LABEL '{ref.target_name}'")
                final.append(
                    Instr(opcode, label_objects[ref.target_name], lineno=ref.lineno)
                )

            else:
                raise RuntimeError(f"unknown placeholder {tag!r}")

        else:
            final.append(it)

    # Sanity pass
    for it in final:
        # no tuple placeholders left
        if isinstance(it, tuple):
            raise RuntimeError(f"unresolved jump placeholder: {it!r}")
        # jumps must target a Label
        if isinstance(it, Instr):
            if it.name in COND_JUMP_OPS | UNCOND_JUMP_FIXED:
                from bytecode import Label as _Lbl

                if not isinstance(it.arg, _Lbl):
                    raise RuntimeError(f"jump still has non-Label arg: {it}")
    return final


def assemble_file(src_path: Path) -> CodeType:
    """
    Parse .paxy -> (Instr stream) -> resolve labels -> Bytecode -> CodeType
    """
    parser = Parser()
    instrs: List[Instr] = parser.parse_file(src_path)

    resolved = _resolve_labels(instrs)

    if os.getenv("PAXY_DEBUG") == "1":
        out: List[str] = []
        out.append("== RESOLVED ==")
        for i, it in enumerate(resolved):
            out.append(f"{i:03d}: {it!r}")
        bc = Bytecode(resolved)
        code = bc.to_code()
        out.append("== DISASSEMBLY ==")
        out.append(_dis.Bytecode(code).dis())  # returns a str in 3.13
        # write to file
        dbg_path = Path(os.getenv("PAXY_DEBUG_OUT", "/tmp/paxy_debug.txt"))
        dbg_path.write_text("\n".join(out))
        return code

    bc = Bytecode(resolved)
    bc.filename = str(src_path)
    bc.name = "<module>"
    # Ensure flags are sane for module code
    bc.flags |= CompilerFlags.NOFREE

    # First instruction lineno is used as first_lineno
    if resolved:
        first = next((x for x in resolved if isinstance(x, Instr)), None)
        if first is not None and first.lineno:
            bc.first_lineno = first.lineno

    code = bc.to_code()

    if os.getenv("PAXY_DEBUG") == "1":
        print("== DISASSEMBLY ==")
        _dis.dis(code)

    return code
