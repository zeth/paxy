# paxy/basic/callfn.py
from __future__ import annotations

from typing import Any

from paxy.basic.base import BasicOperation
from paxy.ident import Ident


class Gosub(BasicOperation):
    """
    CALLFN <dst> <name> [args...]

    Lowers to:
        LOAD_NAME <name>
        <LOAD_* for each arg>
        CALL <nargs>
        STORE_NAME <dst>

    Notes:
    - Do NOT emit PUSH_NULL here. That's only for the method fast-path /
      bit-flagged globals/attrs, not for a plain LOAD_NAME function call.
    """

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) < 2 or not isinstance(op_args[0], Ident):
            raise SyntaxError(
                "CALLFN expects: CALLFN <dst> <name> [args...] (with <dst> an identifier)"
            )

        dst_ident: Ident = op_args[0]
        fn_token = op_args[1]
        args = op_args[2:]

        # Resolve the function object
        if isinstance(fn_token, Ident):
            self.add_op("LOAD_NAME", str(fn_token))
        elif isinstance(fn_token, str):
            # Allow a raw string name too
            self.add_op("LOAD_NAME", fn_token)
        else:
            raise SyntaxError("CALLFN second argument must be a function name")

        # Push positional arguments
        for a in args:
            if isinstance(a, Ident):
                self.add_op("LOAD_NAME", str(a))
            else:
                self.add_op("LOAD_CONST", a)

        # Call and store
        self.add_op("CALL", len(args))
        self.add_op("STORE_NAME", str(dst_ident))
