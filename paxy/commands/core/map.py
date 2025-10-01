# paxy/commands/core/map.py
from __future__ import annotations
from typing import Any, List
from bytecode import Instr
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class MapCommand(Command):
    """
    MAP <dst> [<key> <value> ...]
    Build a dict (map).

    Keys may be:
      - literal strings (e.g. 'name')
      - identifiers whose *runtime value* is a string (e.g. keyvar)

    Values may be literals or identifiers.

    Examples:
      MAP m                       ; {}
      MAP m 'a' 1 'b' 2          ; {'a': 1, 'b': 2}
      LET k "user"
      MAP m k 42                  ; {'user': 42}
    """

    COMMAND = "MAP"

    def make_ops(self, args: list[Any]) -> None:
        if not args:
            raise SyntaxError("MAP expects: MAP <name> [<key> <value> ...]")

        dst = args[0]
        if not isinstance(dst, Ident):
            raise SyntaxError("MAP expects first argument to be an identifier name")

        kv = args[1:]
        if len(kv) == 0:
            # {}
            self.add_op("BUILD_MAP", 0)
            self.add_op("STORE_NAME", str(dst))
            return

        if len(kv) % 2 != 0:
            raise SyntaxError("MAP requires an even number of key/value arguments")

        # BUILD_MAP then MAP_ADD 1 per pair; works on 3.13 and 3.14
        self.add_op("BUILD_MAP", 0)

        # For each (key, value)
        for i in range(0, len(kv), 2):
            k = kv[i]
            v = kv[i + 1]

            # Key: literal string or identifier (runtime string)
            if isinstance(k, Ident):
                self.add_op("LOAD_NAME", str(k))
            elif isinstance(k, str):
                self.add_op("LOAD_CONST", k)
            else:
                # We accept identifiers (runtime strings) or literal strings only.
                # Non-string literals (e.g. 1) are rejected here for clarity/predictability.
                raise SyntaxError("MAP keys must be strings or identifiers")

            # Value: literal or identifier
            if isinstance(v, Ident):
                self.add_op("LOAD_NAME", str(v))
            else:
                self.add_op("LOAD_CONST", v)

            # Add this pair to the map
            self.add_op("MAP_ADD", 1)

        self.add_op("STORE_NAME", str(dst))
