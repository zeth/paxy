# paxy/basic_ops.py
"""Extra BASIC-like commands that lower to CPython bytecode instructions."""
from __future__ import annotations
from typing import Any, List, Tuple
from bytecode import Instr

_NOARG = object()


class BasicOperation:
    def __init__(self, op_arg: Any, lineno: int):
        self.ops: list[Instr] = []
        self.lineno = lineno
        self.make_ops(op_arg)

    def add_op(self, op_name: str, op_arg: Any = _NOARG):
        # Only omit the argument when the caller *really* means “no arg”.
        if op_arg is _NOARG:
            op = Instr(op_name, lineno=self.lineno)
        else:
            op = Instr(op_name, op_arg, lineno=self.lineno)
        self.ops.append(op)

    def make_ops(self, op_arg: Any):
        raise NotImplementedError


class Print(BasicOperation):
    def make_ops(self, op_arg: Any):
        # 3.13 call sequence: LOAD_NAME 'print' ; PUSH_NULL ; [args] ; CALL n ; POP_TOP
        self.add_op("LOAD_NAME", "print")
        self.add_op("PUSH_NULL")
        if op_arg is None:
            self.add_op("CALL", 0)
        else:
            self.add_op("LOAD_CONST", op_arg)
            self.add_op("CALL", 1)
        self.add_op("POP_TOP")


class Let(BasicOperation):
    """LET <identifier> <literal>  ->  LOAD_CONST <literal>; STORE_NAME <identifier>"""
    def make_ops(self, op_arg: Any):
        if not (isinstance(op_arg, tuple) and len(op_arg) == 2 and isinstance(op_arg[0], str)):
            raise SyntaxError("LET expects (name, value)")
        name, value = op_arg  # type: Tuple[str, Any]
        self.add_op("LOAD_CONST", value)
        self.add_op("STORE_NAME", name)


BASIC_OPS = {
    "PRINT": Print,
    "LET": Let,
}

def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS

def basic_op(op_name: str, op_arg: Any, lineno: int):
    return BASIC_OPS[op_name](op_arg, lineno).ops
