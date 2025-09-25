# paxy/basic/callfn.py
from __future__ import annotations

from typing import Any, List
from paxy.basic.base import BasicOperation
from paxy.ident import Ident


class CallFn(BasicOperation):
    """
    CALLFN <dest> <func> [args...]
      - Loads func from globals
      - PUSH_NULL (CPython 3.11+ calling conv)
      - Loads each arg (identifier -> LOAD_NAME, otherwise LOAD_CONST)
      - CALL <argc>
      - STORE_NAME <dest>

    Backward-compat (legacy form): CALLFN <func>
      - Loads func and calls with 0 args, POP_TOP (discard result)
    """

    def make_ops(self, op_args: List[Any]) -> None:  # -> None
        if not op_args:
            raise SyntaxError("CALLFN expects at least one argument")

        # Legacy: CALLFN <func>
        if len(op_args) == 1:
            func = op_args[0]
            if not isinstance(func, Ident):
                raise SyntaxError("CALLFN <func>: func must be an identifier")
            self.add_op("LOAD_NAME", str(func))
            self.add_op("PUSH_NULL")
            self.add_op("CALL", 0)
            self.add_op("POP_TOP")
            return

        # New form: CALLFN <dest> <func> [args...]
        dest, func, *args = op_args

        if not isinstance(dest, Ident):
            raise SyntaxError("CALLFN: <dest> must be an identifier")
        if not isinstance(func, Ident):
            raise SyntaxError("CALLFN: <func> must be an identifier")

        # LOAD function object
        self.add_op("LOAD_NAME", str(func))
        # CPython 3.11+ calling convention
        self.add_op("PUSH_NULL")

        # Load positional args
        for a in args:
            self._emit_load_for(a)

        # CALL with argc
        self.add_op("CALL", len(args))

        # Store result
        self.add_op("STORE_NAME", str(dest))
