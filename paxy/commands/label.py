from __future__ import annotations
from typing import Any
from paxy.commands.base import BasicOperation
from paxy.compiler.ir import Ident
from paxy.compiler.ir import LabelDecl, JumpRef


class LabelOp(BasicOperation):
    """LABEL <identifier>  -> placeholder resolved by assembler to a bytecode.Label()"""

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("LABEL takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("LABEL expects an identifier")
        # Emit a placeholder; assembler will replace with a real bytecode.Label
        self.ops.append(LabelDecl(str(name), self.lineno))


class GotoOp(BasicOperation):
    """GOTO <identifier>  -> resolved by assembler to a concrete jump to <identifier>"""

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("GOTO takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("GOTO expects an identifier")
        # Emit a placeholder; assembler picks forward/backward opcode later
        self.ops.append(JumpRef(str(name), self.lineno))
