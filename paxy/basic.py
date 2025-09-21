"""Extra BASIC-like comands that get replaced by native bytecode instructions."""

from typing import Any
from bytecode import Instr

class BasicOperation:
    def __init__(self, op_arg: Any, lineno: int):
        self.ops = []
        self.lineno = lineno
        self.make_ops(op_arg)
    
    def add_op(self, op_name: str, op_arg: Any=None):
        if op_arg:
            op = Instr(op_name, op_arg, lineno=self.lineno)
        else:
            op = Instr(op_name, lineno=self.lineno)
        self.ops.append(op)

    def make_ops(self, op_arg):
        # Implement This
        pass


class Print(BasicOperation):
    def make_ops(self, op_arg):
        output = str(op_arg)
        self.add_op("LOAD_NAME", "print")
        self.add_op("LOAD_CONST", output)
        self.add_op("CALL", 1)
        self.add_op("POP_TOP")


BASIC_OPS = {"PRINT": Print}


def is_basic_op(op_name: str):
    return op_name in BASIC_OPS


def basic_op(op_name: str, op_arg: Any, lineno: int):
    return BASIC_OPS[op_name](op_arg, lineno).ops
