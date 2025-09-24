from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.ident import Ident  # import the marker


class Let(BasicOperation):
    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 2:
            raise SyntaxError("LET takes exactly two arguments: name and literal")
        name, value = op_args
        if not isinstance(name, Ident):
            raise SyntaxError("LET expects an identifier for the first argument")
        self.add_op("LOAD_CONST", value)
        self.add_op("STORE_NAME", str(name))
