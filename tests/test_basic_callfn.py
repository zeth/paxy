# paxy/basic/callfn.py
from __future__ import annotations

from typing import Any
from paxy.basic.base import BasicOperation
from paxy.ident import Ident


class CallFn(BasicOperation):
    """
    GOSUB <dest> <name> [args...]

    Loads <name>, calls with args, stores result in <dest>.

    Lowers to:
        LOAD_NAME <name>          # or LOAD_GLOBAL; LOAD_NAME is fine at module scope
        <evaluate each arg>
        BUILD_TUPLE <argc>
        CALL_FUNCTION_EX 0        # call with only positional args
        STORE_NAME <dest>
    """

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) < 2:
            raise SyntaxError("GOSUB expects: GOSUB <dest> <name> [args...]")

        dest, name, *args = op_args

        if not isinstance(dest, Ident):
            raise SyntaxError("GOSUB expects an identifier destination")

        # Resolve function name (identifier or quoted string)
        if isinstance(name, Ident):
            func_name = str(name)
        elif isinstance(name, str):
            func_name = name
        else:
            raise SyntaxError("GOSUB function name must be an identifier or string")

        # Load the callable
        self.add_op("LOAD_NAME", func_name)

        # Positional args (left-to-right)
        for a in args:
            self._emit_load_for(a)

        # Pack positional args into a tuple and call
        self.add_op("BUILD_TUPLE", len(args))
        self.add_op("CALL_FUNCTION_EX", 0)

        # Store the return value
        self.add_op("STORE_NAME", str(dest))
