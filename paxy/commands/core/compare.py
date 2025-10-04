# paxy/basic/compare.py
from typing import Any
from paxy.commands.base import Command
from paxy.compiler.opcoerce import coerce_compare_op
from paxy.compiler.ir import Ident


class Compare(Command):
    """CMP <dst> <lhs> <cmp> <rhs>"""

    COMMAND = "CMP"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 4 or not isinstance(op_args[0], Ident):
            raise SyntaxError("CMP expects: CMP <dst> <lhs> <cmp> <rhs>")
        dst, lhs, cmpop, rhs = op_args
        self._emit_load_for(lhs)
        self._emit_load_for(rhs)
        self.add_op("COMPARE_OP", coerce_compare_op(cmpop))
        self.add_op("STORE_NAME", str(dst))
