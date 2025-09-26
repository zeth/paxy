from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.ir import Ident


class InOp(BasicOperation):
    """IN <dst> <needle> <haystack>  -> dst = (needle in haystack)"""

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("IN expects: IN <dst> <needle> <haystack>")
        dst, needle, hay = args
        self._emit_load_for(needle)
        self._emit_load_for(hay)
        self.add_op("CONTAINS_OP", 0)  # 0 -> IN
        self.add_op("STORE_NAME", str(dst))


class NotInOp(BasicOperation):
    """NOTIN <dst> <needle> <haystack>  -> dst = (needle not in haystack)"""

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("NOTIN expects: NOTIN <dst> <needle> <haystack>")
        dst, needle, hay = args
        self._emit_load_for(needle)
        self._emit_load_for(hay)
        self.add_op("CONTAINS_OP", 1)  # 1 -> NOT_IN
        self.add_op("STORE_NAME", str(dst))
