# paxy/basic/callfn.py
from __future__ import annotations

from typing import Any, List
from paxy.basic.base import BasicOperation
from paxy.ident import Ident


class CallFn(BasicOperation):
    """
    CALLFN <dest> <name> [args...]
      - Loads global <name>, calls with args, stores result in <dest>.
    """

    def make_ops(self, op_args: List[Any]) -> None:
        if len(op_args) < 2:
            raise SyntaxError("CALLFN expects: CALLFN <dest> <name> [args...]")

        dest, fn, *args = op_args
        if not isinstance(dest, Ident):
            raise SyntaxError("CALLFN: <dest> must be an identifier")
        if not isinstance(fn, Ident):
            raise SyntaxError("CALLFN: <name> must be an identifier")

        # Correct stack order for 3.13:
        #   LOAD_GLOBAL (False, name)
        #   PUSH_NULL
        #   <args...>
        #   CALL nargs
        self.add_op("LOAD_GLOBAL", (False, str(fn)))  # function first
        self.add_op("PUSH_NULL")  # then the null sentinel

        for a in args:
            if isinstance(a, Ident):
                self.add_op("LOAD_NAME", str(a))
            else:
                self.add_op("LOAD_CONST", a)

        self.add_op("CALL", len(args))
        self.add_op("STORE_NAME", str(dest))
