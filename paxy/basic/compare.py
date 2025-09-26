# paxy/basic/compare.py
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.opcoerce import coerce_compare_op
from paxy.ir import Ident


class CompareOp(BasicOperation):
    """COMPARE <dst> <lhs> <cmp> <rhs>"""

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 4 or not isinstance(args[0], Ident):
            raise SyntaxError("COMPARE expects: COMPARE <dst> <lhs> <cmp> <rhs>")
        dst, lhs, cmpop, rhs = args
        self._emit_load_for(lhs)
        self._emit_load_for(rhs)
        self.add_op("COMPARE_OP", coerce_compare_op(cmpop))
        self.add_op("STORE_NAME", str(dst))
