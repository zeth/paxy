from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class MapCommand(Command):
    """
    MAP <name> [k1 v1 k2 v2 ...]
      -> <name> = {k1: v1, k2: v2, ...}

    Keys may be:
      - literal strings: 'a', "foo"
      - identifiers: k, key_name   (value looked up at runtime)

    Values may be identifiers or literals.

    Lowering (3.14-friendly):
        BUILD_MAP 0
        # for each (k, v) pair in order:
        <LOAD key>       # LOAD_CONST "a"  or LOAD_NAME k
        <LOAD value>     # LOAD_CONST 1    or LOAD_NAME v
        MAP_ADD 1
        ...
        STORE_NAME <name>
    """

    COMMAND = "MAP"

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError(
                "MAP expects: MAP <name> [k v ...] (name must be an identifier)"
            )
        dst_ident = str(args[0])
        rest = args[1:]

        if len(rest) % 2 != 0:
            raise SyntaxError("MAP expects an even number of key/value arguments")

        # Start with an empty dict and append with MAP_ADD
        self.add_op("BUILD_MAP", 0)

        # Add each (key, value) pair
        for i in range(0, len(rest), 2):
            key_tok = rest[i]
            val_tok = rest[i + 1]

            # Keys: allow Ident (runtime), or literal str. Disallow other literal types.
            if isinstance(key_tok, Ident):
                self.add_op("LOAD_NAME", str(key_tok))
            elif isinstance(key_tok, str):
                self.add_op("LOAD_CONST", key_tok)
            else:
                # Not an identifier and not a string literal => reject
                raise SyntaxError("MAP keys must be literal strings or identifiers")

            # Value (identifier or literal)
            self._emit_load_for(val_tok)

            # Insert one item
            self.add_op("MAP_ADD", 1)

        # Bind to the destination name
        self.add_op("STORE_NAME", dst_ident)
