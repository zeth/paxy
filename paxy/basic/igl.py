# paxy/basic/igl.py
from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.compiler.ir import Ident


class IglOp(BasicOperation):
    """
    IGL <name> [elem1 elem2 ...]  -> name = frozenset({elem1, ...})
    Fast path: all literals & hashable -> LOAD_CONST frozenset(...)
    Fallback: mixed -> LOAD_NAME 'frozenset'; LOAD_*...; BUILD_TUPLE N; CALL 1
    """

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("IGL expects: IGL <name> [elem ...]")
        dst_ident = str(args[0])
        elems = args[1:]

        # Fast path: all literals and hashable
        if all(not isinstance(e, Ident) for e in elems):
            try:
                konst = frozenset(elems)
            except TypeError as exc:
                # unhashable literal (e.g., list) — must use fallback
                konst = None
            if konst is not None:
                self.add_op("LOAD_CONST", konst)
                self.add_op("STORE_NAME", dst_ident)
                return

        # Fallback: build at runtime via function call
        # Stack order for CALL: push callable first, then arguments
        self.add_op("LOAD_NAME", "frozenset")
        for e in elems:
            self._emit_load_for(e)
        self.add_op("BUILD_TUPLE", len(elems))  # frozenset(iterable)
        self.add_op("CALL", 1)
        self.add_op("STORE_NAME", dst_ident)
