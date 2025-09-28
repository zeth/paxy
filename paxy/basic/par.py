from __future__ import annotations
from typing import Any
from paxy.basic.base import BasicOperation
from paxy.compiler.ir import Ident  # you renamed to ir.py


class Par(BasicOperation):
    """
    PAR <dst1> <dst2> <expr1> <expr2>

    Parallel assignment:
        dst1, dst2 = expr1, expr2

    Emission order:
        <load expr1>
        <load expr2>
        STORE_NAME <dst2>
        STORE_NAME <dst1>

    Notes:
      - Works at module scope and inside SUBs.
      - Your assembler will rewrite NAME↔FAST where appropriate.
      - Later we can peephole two STORE_FAST into STORE_FAST_STORE_FAST (3.13 fused).
    """

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 4:
            raise SyntaxError("PAR expects: PAR <dst1> <dst2> <expr1> <expr2>")
        d1, d2, e1, e2 = op_args
        if not isinstance(d1, Ident) or not isinstance(d2, Ident):
            raise SyntaxError("PAR destinations must be identifiers")

        # Evaluate RHS in order
        self._emit_load_for(e1)
        self._emit_load_for(e2)

        # Store in reverse order to avoid clobber
        self.add_op("STORE_NAME", str(d2))
        self.add_op("STORE_NAME", str(d1))
