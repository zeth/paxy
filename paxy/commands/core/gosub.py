# paxy/basic/gosub.py
"""
GOS <dst> <name> [args...] -> LOAD_GLOBAL (True, <name>); <LOAD_* args>; CALL N; STORE_NAME <dst>

Rationale:
- Using LOAD_GLOBAL (True, name) on 3.13 pushes a NULL under the callable,
- so CALL N is valid even without PRECALL (handy when 'bytecode' lacks PRECALL).

"""

from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class Gosub(Command):
    """
    Call a subroutine and store its return value.


    GOS <dst> <name> [args...]

    Call subroutine `name` with arguments and store the return value in `dst`.

    Example:
      GOS total add x y
    """

    COMMAND = "GOS"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) < 2 or not isinstance(op_args[0], Ident):
            raise SyntaxError("GOS expects: GOS <dst> <name> [args...]")

        dst_ident: Ident = op_args[0]
        fn_token = op_args[1]
        args = op_args[2:]

        # Resolve callable: accept Ident or str
        if isinstance(fn_token, Ident):
            fn_name = str(fn_token)
        elif isinstance(fn_token, str):
            fn_name = fn_token
        else:
            raise SyntaxError("GOS second argument must be a subroutine name")

        # 3.13 pattern without PRECALL: NULL comes from LOAD_GLOBAL(True, name)
        self.add_op("LOAD_GLOBAL", (True, fn_name))

        # Positional args
        for a in args:
            if isinstance(a, Ident):
                self.add_op("LOAD_NAME", str(a))
            else:
                self.add_op("LOAD_CONST", a)

        # Direct call & store
        self.add_op("CALL", len(args))
        self.add_op("STORE_NAME", str(dst_ident))
