from typing import Any
from paxy.commands.base import Command


class ImportSimple(Command):
    """
    IMP 'module'
    Lowers to: LOAD_NAME '__import__'; PUSH_NULL; LOAD_CONST 'module'; CALL 1; POP_TOP
    (No binding; the module is added to sys.modules by __import__)
    """

    COMMAND = "IMP"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("IMP takes exactly one string literal")
        mod = op_args[0]
        if not isinstance(mod, str):
            raise SyntaxError("IMP expects a string literal module name")
        self.add_op("LOAD_NAME", "__import__")
        self.add_op("PUSH_NULL")
        self.add_op("LOAD_CONST", mod)
        self.add_op("CALL", 1)
        self.add_op("POP_TOP")
