from __future__ import annotations
from typing import Any

from paxy.basic.let import Let
from paxy.basic.print import Print
from paxy.basic.input import Input
from paxy.basic.importer import ImportSimple
from paxy.basic.callfn import CallFn

BASIC_OPS = {
    "PRINT": Print,
    "LET": Let,
    "INPUT": Input,
    "IMPORT": ImportSimple,   # NEW
    "CALLFN": CallFn,         # NEW (avoid clash with native CALL opcode)
}

def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS

def basic_op(op_name: str, op_arg: Any, lineno: int):
    return BASIC_OPS[op_name](op_arg, lineno).ops
