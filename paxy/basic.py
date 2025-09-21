"""Extra BASIC-like commands that lower to CPython bytecode instructions."""
from __future__ import annotations
from typing import Any, List
from bytecode import Instr

class BasicOperation:
    def __init__(self, op_arg: Any, lineno: int):
        self.ops: List[Instr] = []
        self.lineno = lineno
        self.make_ops(op_arg)

    def add_op(self, op_name: str, op_arg: Any = None):
        # Keep falsy-but-valid args like 0, "", False
        if op_arg is not None:
            op = Instr(op_name, op_arg, lineno=self.lineno)
        else:
            op = Instr(op_name, lineno=self.lineno)
        self.ops.append(op)

    def make_ops(self, op_arg: Any):
        raise NotImplementedError


class Print(BasicOperation):
    """
    PRINT <arg?>
    - If arg is omitted, prints a blank line (PRINT None -> print()).
    - If arg is ExplicitNone sentinel, treat as Python None.
    """
    def make_ops(self, op_arg: Any):
        # 3.13 call sequence: LOAD_NAME 'print' ; PUSH_NULL ; ...args... ; CALL n ; POP_TOP
        self.add_op("LOAD_NAME", "print")
        self.add_op("PUSH_NULL")
        if op_arg is None:
            # no args -> print()
            self.add_op("CALL", 0)
        else:
            self.add_op("LOAD_CONST", op_arg)
            self.add_op("CALL", 1)
        self.add_op("POP_TOP")


BASIC_OPS = {
    "PRINT": Print,
}

def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS

def basic_op(op_name: str, op_arg: Any, lineno: int):
    return BASIC_OPS[op_name](op_arg, lineno).ops
