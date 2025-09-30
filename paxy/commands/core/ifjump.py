# paxy/basic/ifjump.py

from typing import Any
from paxy.commands.base import Command
from paxy.compiler.opcoerce import coerce_compare_op
from paxy.compiler.ir import Ident
from paxy.compiler.ir import NamedJump


class IfOp(Command):
    """
    IF <lhs> <cmp> <rhs> <label>
      - compares lhs <cmp> rhs
      - jumps to <label> if the comparison is true
    Examples:
      IF a '==' b done
      IF n '<=' 0 exit
    """

    COMMAND = "IF"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 4:
            raise SyntaxError("IF expects: IF <lhs> <cmp> <rhs> <label>")

        lhs, cmpop, rhs, label = args

        if not isinstance(label, Ident):
            raise SyntaxError("IF expects a label identifier as the fourth argument")

        # LOAD lhs
        if isinstance(lhs, Ident):
            self.add_op("LOAD_NAME", str(lhs))
        else:
            self.add_op("LOAD_CONST", lhs)

        # LOAD rhs
        if isinstance(rhs, Ident):
            self.add_op("LOAD_NAME", str(rhs))
        else:
            self.add_op("LOAD_CONST", rhs)

        # COMPARE_OP (supports symbols or enum names; coercer handles both)
        self.add_op("COMPARE_OP", coerce_compare_op(cmpop))

        # Jump if true (assembler will resolve NamedJump to real Label arg)
        self.ops.append(NamedJump("POP_JUMP_IF_TRUE", str(label), self.lineno))
