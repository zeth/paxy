from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident
from paxy.compiler.ir import LabelDecl, JumpRef


class LabelCommand(Command):
    """LBL <identifier>  -> placeholder resolved by assembler to a bytecode.Label()"""

    COMMAND = "LBL"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("LBL takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("LBL expects an identifier")
        # Emit a placeholder; assembler will replace with a real bytecode.Label
        self.ops.append(LabelDecl(str(name), self.lineno))


class GotoCommand(Command):
    """GO <identifier>  -> resolved by assembler to a concrete jump to <identifier>"""

    COMMAND = "GO"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("GO takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("GO expects an identifier")
        # Emit a placeholder; assembler picks forward/backward opcode later
        self.ops.append(JumpRef(str(name), self.lineno))
