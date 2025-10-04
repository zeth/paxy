from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class MapDel(Command):
    """
    MAL <map> <key>
      -> del <map>[<key>]
    """

    COMMAND = "MAL"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 2 or not isinstance(op_args[0], Ident):
            raise SyntaxError("MAL expects: MAL <map> <key>")

        mapname, key = op_args
        self.add_op("LOAD_NAME", str(mapname))
        self._emit_load_for(key)
        self.add_op("DELETE_SUBSCR")
