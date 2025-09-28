from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class Input(Command):
    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("INPUT takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("INPUT expects an identifier")
        self.add_op("LOAD_NAME", "input")
        self.add_op("PUSH_NULL")
        self.add_op("CALL", 0)
        self.add_op("STORE_NAME", str(name))
