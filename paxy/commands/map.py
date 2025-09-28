from typing import Any
from paxy.commands.base import BasicOperation
from paxy.compiler.ir import Ident


class MapOp(BasicOperation):
    """
    MAP <name> [k1 v1 k2 v2 ...]
      -> <name> = {k1: v1, k2: v2, ...}
    Rules:
      - Keys MUST be literal strings (JSON-style), not identifiers.
      - Number of items after <name> must be even.
      - Values may be identifiers or literals.

    Lowering (fast path):
      LOAD_CONST (k1, k2, ..., kn)     # tuple of constant string keys
      ... emit v1, v2, ..., vn ...
      BUILD_CONST_KEY_MAP n
      STORE_NAME <name>
    """

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError(
                "MAP expects: MAP <name> [k v ...] (name must be an identifier)"
            )
        dst = str(args[0])
        rest = args[1:]

        if len(rest) % 2 != 0:
            raise SyntaxError(
                "MAP expects an even number of elements after the name: k v k v ..."
            )

        # Split into keys / values and validate keys are literal strings
        keys: list[str] = []
        vals: list[Any] = []
        for i in range(0, len(rest), 2):
            k = rest[i]
            v = rest[i + 1]
            if isinstance(k, Ident):
                raise SyntaxError("MAP keys must be literal strings (not identifiers)")
            if not isinstance(k, str):
                raise SyntaxError(
                    f"MAP keys must be strings (got {type(k).__name__!s})"
                )
            keys.append(k)
            vals.append(v)

        # Emit: LOAD_CONST (keys...), then the values, then BUILD_CONST_KEY_MAP
        self.add_op("LOAD_CONST", tuple(keys))
        for v in vals:
            self._emit_load_for(v)
        self.add_op("BUILD_CONST_KEY_MAP", len(keys))
        self.add_op("STORE_NAME", dst)
