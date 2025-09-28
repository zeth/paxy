# paxy/basic/row.py
from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class RowCommand(Command):
    """
    ROW <name> [elem1 elem2 ...]  -> name = (elem1, elem2, ...)
    Fast path: all literals -> LOAD_CONST (tuple)
    Fallback: mixed idents/literals -> LOAD_*...; BUILD_TUPLE N
    """

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("ROW expects: ROW <name> [elem ...]")
        dst_ident = str(args[0])
        elems = args[1:]

        # Fast path: all literals
        if all(not isinstance(e, Ident) for e in elems):
            self.add_op("LOAD_CONST", tuple(elems))
            self.add_op("STORE_NAME", dst_ident)
            return

        # Fallback: builder path
        for e in elems:
            self._emit_load_for(e)
        self.add_op("BUILD_TUPLE", len(elems))
        self.add_op("STORE_NAME", dst_ident)
