from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class IsCommand(Command):
    """IS <dst> <lhs> <rhs>  -> dst = (lhs is rhs)"""

    COMMAND = "IS"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("IS expects: IS <dst> <lhs> <rhs>")
        dst, lhs, rhs = args
        self._emit_load_for(lhs)
        self._emit_load_for(rhs)
        self.add_op("IS_OP", 0)  # 0 -> IS
        self.add_op("STORE_NAME", str(dst))


class IsNotCommand(Command):
    """NIS <dst> <lhs> <rhs>  -> dst = (lhs is not rhs)"""

    COMMAND = "NIS"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("NIS expects: NIS <dst> <lhs> <rhs>")
        dst, lhs, rhs = args
        self._emit_load_for(lhs)
        self._emit_load_for(rhs)
        self.add_op("IS_OP", 1)  # 1 -> IS_NOT
        self.add_op("STORE_NAME", str(dst))
