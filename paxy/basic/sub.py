from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.ident import Ident


class GoSubOp(BasicOperation):
    """
    GOSUB <name> [arg ...]
      -> LOAD_NAME <name>; PUSH_NULL; <args>; CALL N; POP_TOP
    """

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("GOSUB expects: GOSUB <name> [args...]")

        fn_name = str(args[0])
        call_args = args[1:]

        self.add_op("LOAD_NAME", fn_name)
        self.add_op("PUSH_NULL")
        for a in call_args:
            self._emit_load_for(a)
        self.add_op("CALL", len(call_args))
        self.add_op("POP_TOP")
