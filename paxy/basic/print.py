from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation

class Print(BasicOperation):
    def make_ops(self, op_args: list[Any]):
        if len(op_args) > 1:
            raise SyntaxError("PRINT takes at most one argument")
        self.add_op("LOAD_NAME", "print")
        self.add_op("PUSH_NULL")
        if len(op_args) == 0:
            self.add_op("CALL", 0)
        else:
            self.add_op("LOAD_CONST", op_args[0])
            self.add_op("CALL", 1)
        self.add_op("POP_TOP")
