# paxy/basic/mapadd.py
from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.ident import Ident


class MapAddOp(BasicOperation):
    """
    MAPADD <map> <key> <value>
      -> <map>[<key>] = <value>

    Example:
        MAP m 'a' 1
        MAPADD m 'b' 2
    """

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("MAPADD expects: MAPADD <map> <key> <value>")
        mapname, key, val = args

        # LOAD_NAME m
        self.add_op("LOAD_NAME", str(mapname))

        # LOAD key
        self._emit_load_for(key)

        # LOAD value
        self._emit_load_for(val)

        # STORE_SUBSCR (does m[key] = val)
        self.add_op("STORE_SUBSCR")
