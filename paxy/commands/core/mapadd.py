# paxy/basic/MAD.py
from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class Mad(Command):
    """
    MAD <map> <key> <value>
      -> <map>[<key>] = <value>

    Example:
        MAP m 'a' 1
        MAD m 'b' 2
    """

    COMMAND = "MAD"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("MAD expects: MAD <map> <key> <value>")
        mapname, key, val = args

        # LOAD_NAME m
        self.add_op("LOAD_NAME", str(mapname))

        # LOAD key
        self._emit_load_for(key)

        # LOAD value
        self._emit_load_for(val)

        # STORE_SUBSCR (does m[key] = val)
        self.add_op("STORE_SUBSCR")
