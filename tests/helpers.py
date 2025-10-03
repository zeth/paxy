from __future__ import annotations
from pathlib import Path
from bytecode import Bytecode, CompilerFlags
from bytecode.instr import _UNSET as _UNSET_CTOR
from typing import Any
from types import CodeType

from paxy.compiler.parser import Parser
from paxy.compiler.ir import ParsedItem
from paxy.compiler.twelve import normalize_push_null_for_calls_312_seq


UNSET = _UNSET_CTOR()


def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]


def get_instrs(src: Path) -> list[ParsedItem]:
    instrs: list[ParsedItem] = Parser().parse_file(src)
    # 3.12 call-site canonicalization
    instrs = normalize_push_null_for_calls_312_seq(instrs)
    return instrs


def _dump_debug(instrs: list[ParsedItem], title: str = "== HELPER RESOLVED ==") -> None:
    try:
        with open("/tmp/paxy_debug.txt", "a", encoding="utf-8") as f:
            f.write(f"{title}\n")
            for idx, ins in enumerate(instrs):
                f.write(f"{idx:03d}: {ins!r}\n")
    except Exception:
        pass  # never let debug crash tests


def run_paxy_path(src: Path, *, filename: str = "<string>") -> dict[str, Any]:
    instrs = get_instrs(src)
    # dump BEFORE exec so we can see what actually ran
    _dump_debug(instrs, "== HELPER RESOLVED ==")

    bc = Bytecode(instrs)
    bc.filename = filename
    bc.name = "<module>"
    bc.first_lineno = getattr(instrs[0], "lineno", 1)
    bc.flags |= CompilerFlags.NOFREE

    code: CodeType = bc.to_code()
    g: dict[str, Any] = {"__name__": "__main__"}
    exec(code, g)
    return g
