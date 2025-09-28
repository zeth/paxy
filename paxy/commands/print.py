from typing import Any
from paxy.commands.base import BasicOperation


class Print(BasicOperation):
    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) > 1:
            raise SyntaxError("PRINT takes at most one argument")

        # Load builtin print and prepare CALL convention
        self.add_op("LOAD_NAME", "print")
        self.add_op("PUSH_NULL")

        if len(op_args) == 0:
            # print()
            self.add_op("CALL", 0)
        else:
            # print(<arg>) — load identifier as name, literal as const
            self._emit_load_for(op_args[0])
            self.add_op("CALL", 1)

        self.add_op("POP_TOP")
