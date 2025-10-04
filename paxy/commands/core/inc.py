# paxy/basic/inc.py
from typing import Any

from paxy.commands.base import Command
from paxy.compiler.ir import Ident
from paxy.compiler.opcoerce import coerce_binary_op


class Inc(Command):
    COMMAND = "INC"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1 or not isinstance(op_args[0], Ident):
            raise SyntaxError("INC expects: INC <name>")
        name = str(op_args[0])
        self.add_op("LOAD_NAME", name)
        self.add_op("LOAD_CONST", 1)
        self.add_op("BINARY_OP", coerce_binary_op("+"))
        self.add_op("STORE_NAME", name)
