from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.compiler.ir import ReturnMarker


class ReturnOp(BasicOperation):
    """
    RETURN [value]
      - RETURN               -> RETURN_CONST None  (3.13 emits RETURN_CONST 0)
      - RETURN <expr>        -> push <expr>, RETURN_VALUE
    """

    def make_ops(self, args: list[Any]) -> None:
        if len(args) == 0:
            self.ops.append(ReturnMarker(has_value=False, lineno=self.lineno))
            return
        if len(args) == 1:
            self._emit_load_for(args[0])
            self.ops.append(ReturnMarker(has_value=True, lineno=self.lineno))
            return
        raise SyntaxError("RETURN takes at most one argument")
