from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.ident import Ident


class Input(BasicOperation):
    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("INPUT takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("INPUT expects an identifier")
        self.add_op("LOAD_NAME", "input")
        self.add_op("PUSH_NULL")
        self.add_op("CALL", 0)
        self.add_op("STORE_NAME", str(name))
