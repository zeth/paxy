from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class InCommand(Command):
    """IN <dst> <needle> <haystack>  -> dst = (needle in haystack)"""

    COMMAND = "IN"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("IN expects: IN <dst> <needle> <haystack>")
        dst, needle, hay = args
        self._emit_load_for(needle)
        self._emit_load_for(hay)
        self.add_op("CONTAINS_OP", 0)  # 0 -> IN
        self.add_op("STORE_NAME", str(dst))


class NotInCommand(Command):
    """NIN <dst> <needle> <haystack>  -> dst = (needle not in haystack)"""

    COMMAND = "NIN"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("NIN expects: NIN <dst> <needle> <haystack>")
        dst, needle, hay = args
        self._emit_load_for(needle)
        self._emit_load_for(hay)
        self.add_op("CONTAINS_OP", 1)  # 1 -> NOT_IN
        self.add_op("STORE_NAME", str(dst))
