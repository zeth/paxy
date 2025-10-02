from __future__ import annotations
from pathlib import Path
from bytecode import Bytecode, CompilerFlags
from bytecode.instr import _UNSET as _UNSET_CTOR
from typing import Any
from types import CodeType

from paxy.compiler.parser import Parser
from paxy.compiler.ir import ParsedItem
from paxy.compiler.opcoerce import normalize_push_null_for_calls_312_seq


UNSET = _UNSET_CTOR()


def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]


def get_instrs(src: Path) -> list[ParsedItem]:
    instrs: list[ParsedItem] = Parser().parse_file(src)
    return normalize_push_null_for_calls_312_seq(instrs)


def run_paxy_path(src: Path, *, filename: str = "<string>") -> dict[str, Any]:
    instrs: list[ParsedItem] = get_instrs(src)

    bc = Bytecode(instrs)
    bc.filename = filename
    bc.name = "<module>"
    bc.first_lineno = getattr(instrs[0], "lineno", 1)
    bc.flags |= CompilerFlags.NOFREE

    code: CodeType = bc.to_code()
    g: dict[str, Any] = {"__name__": "__main__"}
    exec(code, g)
    return g
