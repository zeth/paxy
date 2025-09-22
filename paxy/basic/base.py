from __future__ import annotations
from bytecode import Instr
from typing import Any, Sequence

_NOARG = object()

class BasicOperation:
    def __init__(self, op_args: Sequence[Any], lineno: int):
        self.ops: list[Instr] = []
        self.lineno = lineno
        self.make_ops(list(op_args))  # copy for safety

    def add_op(self, op_name: str, op_arg: Any = _NOARG):
        if op_arg is _NOARG:
            op = Instr(op_name, lineno=self.lineno)
        else:
            op = Instr(op_name, op_arg, lineno=self.lineno)
        self.ops.append(op)

    def make_ops(self, op_args: list[Any]):
        raise NotImplementedError
