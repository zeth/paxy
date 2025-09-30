from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident  # you renamed to ir.py


class Par(Command):
    """
    PAR <dst1> <dst2> <expr1> <expr2>

    Parallel assignment:
        dst1, dst2 = expr1, expr2

    Emission order:
        <load expr1>
        <load expr2>
        STORE_NAME <dst2>
        STORE_NAME <dst1>

    The PAR command implements *parallel assignment*, a feature where multiple
    variables are updated at the same time from multiple expressions.

    In ordinary sequential assignment, temporary variables or explicit ordering
    are needed to avoid overwriting values. For example, swapping two variables
    with LET would normally require introducing a third variable. With PAR, both
    targets receive their new values simultaneously, so expressions are evaluated
    before any assignments take effect.

    This makes PAR useful for:
    - cleanly expressing swaps or rotations without temporaries,
    - tuple-style unpacking (a, b = expr1, expr2),
    - making algorithms like Fibonacci or Euclidean GCD concise and efficient.

    Notes:
      - Works at module scope and inside SUBs.
      - The assembler will rewrite NAME↔FAST where appropriate.
    """

    COMMAND = "PAR"

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
