from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.ident import Ident

class CallFn(BasicOperation):
    """
    CALLFN <identifier>   # zero-arg call
    Lowers to: LOAD_NAME name; PUSH_NULL; CALL 0; POP_TOP
    """
    def make_ops(self, op_args: list[Any]):
        if len(op_args) != 1:
            raise SyntaxError("CALLFN takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("CALLFN expects an identifier")
        self.add_op("LOAD_NAME", str(name))
        self.add_op("PUSH_NULL")
        self.add_op("CALL", 0)
        self.add_op("POP_TOP")
