# paxy/basic/__init__.py
"""Extra BASIC-like commands that lower to CPython bytecode instructions."""
from __future__ import annotations
from typing import Any, Tuple

from paxy.basic.let import Let
from paxy.basic.print import Print


BASIC_OPS = {
    "PRINT": Print,
    "LET": Let,
}

def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS

def basic_op(op_name: str, op_arg: Any, lineno: int):
    return BASIC_OPS[op_name](op_arg, lineno).ops
