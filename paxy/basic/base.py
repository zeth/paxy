from bytecode import Instr
from typing import Any

_NOARG = object()

class BasicOperation:
    def __init__(self, op_arg: Any, lineno: int):
        self.ops: list[Instr] = []
        self.lineno = lineno
        self.make_ops(op_arg)

    def add_op(self, op_name: str, op_arg: Any = _NOARG):
        # Only omit the argument when the caller *really* means “no arg”.
        if op_arg is _NOARG:
            op = Instr(op_name, lineno=self.lineno)
        else:
            op = Instr(op_name, op_arg, lineno=self.lineno)
        self.ops.append(op)

    def make_ops(self, op_arg: Any):
        raise NotImplementedError
