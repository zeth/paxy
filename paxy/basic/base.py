# paxy/basic/base.py
from __future__ import annotations

from typing import Any, Union
from bytecode import Instr, BinaryOp
from paxy.opcoerce import coerce_binary_op
from paxy.labels import LabelDecl, JumpRef

_NOARG = object()

# Names should match bytecode's BinaryOp (3.12/3.13)
BINARY_SYMBOL_MAP: dict[str, str] = {
    "+": "ADD",
    "-": "SUBTRACT",
    "*": "MULTIPLY",
    "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE",
    "%": "REMAINDER",
    "**": "POWER",
    "<<": "LSHIFT",
    ">>": "RSHIFT",
    "|": "OR",
    "&": "AND",
    "^": "XOR",
    "@": "MATRIX_MULTIPLY",
}

# What BASIC ops may emit
BasicItem = Union[Instr, LabelDecl, JumpRef]


class BasicOperation:
    def __init__(self, op_args: list[Any], lineno: int) -> None:
        self.ops: list[BasicItem] = []
        self.lineno: int = lineno
        self.make_ops(op_args)

    def _coerce_arg(self, op_name: str, arg: Any) -> Any:
        if op_name == "BINARY_OP" and isinstance(arg, str):
            name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
            return BinaryOp[name]
        return arg

    def add_op(self, op_name: str, op_arg: Any = _NOARG) -> None:
        if op_arg is _NOARG:
            op = Instr(op_name, lineno=self.lineno)
        else:
            coerced = coerce_binary_op(op_arg) if op_name == "BINARY_OP" else op_arg
            op = Instr(op_name, coerced, lineno=self.lineno)
        self.ops.append(op)

    def make_ops(self, op_args: list[Any]) -> None:
        raise NotImplementedError
