from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class MapDel(Command):
    """
    MAPDEL <map> <key>
      -> del <map>[<key>]
    """

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2 or not isinstance(args[0], Ident):
            raise SyntaxError("MAPDEL expects: MAPDEL <map> <key>")
        mapname, key = args

        # LOAD_NAME map
        self.add_op("LOAD_NAME", str(mapname))
        # LOAD key
        self._emit_load_for(key)
        # DELETE_SUBSCR (performs: del map[key])
        self.add_op("DELETE_SUBSCR")
