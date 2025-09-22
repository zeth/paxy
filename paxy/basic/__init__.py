from __future__ import annotations
from typing import Any

from paxy.basic.let import Let
from paxy.basic.print import Print
from paxy.basic.input import Input

BASIC_OPS = {
    "PRINT": Print,
    "LET": Let,
    "INPUT": Input,
}

def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS

def basic_op(op_name: str, op_arg: Any, lineno: int):
    # op_arg is actually the *list* of args now
    return BASIC_OPS[op_name](op_arg, lineno).ops
