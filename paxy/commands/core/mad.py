from typing import Any

from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class Mad(Command):
    """
    MAD <map> <key> <value>
      -> <map>[<key>] = <value>
    """

    COMMAND = "MAD"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 3 or not isinstance(op_args[0], Ident):
            raise SyntaxError("MAD expects: MAD <map> <key> <value>")

        mapname, key, val = op_args
        self.add_op("LOAD_NAME", str(mapname))
        self._emit_load_for(key)
        self._emit_load_for(val)
        self.add_op("STORE_SUBSCR")
