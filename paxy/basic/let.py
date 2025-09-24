# paxy/basic/let.py
from __future__ import annotations
from typing import Any, Tuple
from paxy.basic.base import BasicOperation
from paxy.ident import Ident
from paxy.opcoerce import (
    coerce_binary_op,
    coerce_compare_op,
    coerce_contains_op,
    coerce_is_op,
)


class Let(BasicOperation):
    """
    LET <name> <value>
    LET <name> <lhs> <op> <rhs>     # op: +, -, *, //, ==, <=, is, in, not in, etc.
    """

    def make_ops(self, args: list[Any]) -> None:
        dst_ident, rest = self._parse_head(args)

        if len(rest) == 1:
            self._emit_simple_assignment(dst_ident, rest[0])
            return

        if len(rest) == 3:
            lhs, op, rhs = rest
            self._emit_operator_assignment(dst_ident, lhs, op, rhs)
            return

        raise SyntaxError("LET operator form: LET <name> <lhs> <op> <rhs>")

    # ---------- parsing / validation ----------

    def _parse_head(self, args: list[Any]) -> tuple[Ident, list[Any]]:
        if len(args) < 2:
            raise SyntaxError("LET expects at least: LET <name> <value>")
        name = args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("LET expects an identifier as the first argument")
        return name, args[1:]

    # ---------- simple form ----------

    def _emit_simple_assignment(self, dst_ident: Ident, value: Any) -> None:
        self._emit_load(value)
        self._emit_store(dst_ident)

    # ---------- operator form ----------

    def _emit_operator_assignment(
        self, dst_ident: Ident, lhs: Any, op: Any, rhs: Any
    ) -> None:
        self._emit_load(lhs)
        self._emit_load(rhs)
        kind, coerced = self._classify_and_coerce_op(op)
        self._emit_op(kind, coerced)
        self._emit_store(dst_ident)

    # ---------- tiny primitives ----------

    def _emit_load(self, value: Any) -> None:
        if isinstance(value, Ident):
            self.add_op("LOAD_NAME", str(value))
        else:
            self.add_op("LOAD_CONST", value)

    def _emit_store(self, ident: Ident) -> None:
        self.add_op("STORE_NAME", str(ident))

    # ---------- operator classification ----------

    def _classify_and_coerce_op(self, op: Any) -> Tuple[str, Any]:
        """
        Try comparison → identity → membership → binary.
        Returns (kind, coerced_arg) where kind ∈ {"COMPARE_OP","IS_OP","CONTAINS_OP","BINARY_OP"}.
        """
        text = str(op)

        # comparisons: == != < <= > >=
        try:
            return "COMPARE_OP", coerce_compare_op(text)
        except SyntaxError:
            pass

        # identity: is / is not
        try:
            return "IS_OP", coerce_is_op(text)
        except SyntaxError:
            pass

        # membership: in / not in
        try:
            return "CONTAINS_OP", coerce_contains_op(text)
        except SyntaxError:
            pass

        # fall back to binary arithmetic/bitwise
        return "BINARY_OP", coerce_binary_op(text)

    def _emit_op(self, kind: str, coerced: Any) -> None:
        # All these opcodes take exactly one argument
        self.add_op(kind, coerced)
