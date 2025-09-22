from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation

class Input(BasicOperation):
    """INPUT <identifier>  ->  LOAD_NAME 'input'; PUSH_NULL; CALL 0; STORE_NAME <identifier>"""
    def make_ops(self, op_args: list[Any]):
        if len(op_args) != 1:
            raise SyntaxError("INPUT takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, str):
            raise SyntaxError("INPUT expects an identifier")
        self.add_op("LOAD_NAME", "input")
        self.add_op("PUSH_NULL")
        self.add_op("CALL", 0)
        self.add_op("STORE_NAME", name)
