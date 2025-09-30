"""Decrement variable by one."""

# paxy/basic/dec.py
from typing import Any
from bytecode import BinaryOp
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class Dec(Command):

    COMMAND = "DEC"
    SUMMARY = "Add description here."

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("DEC takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("DEC expects an identifier")

        ident = str(name)

        self.add_op("LOAD_NAME", ident)
        self.add_op("LOAD_CONST", 1)
        self.add_op("BINARY_OP", BinaryOp.SUBTRACT)  # <-- enum, not str
        self.add_op("STORE_NAME", ident)
