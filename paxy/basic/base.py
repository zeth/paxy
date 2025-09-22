# paxy/basic/base.py
from bytecode import Instr, BinaryOp
from typing import Any
from paxy.opcoerce import coerce_binary_op

_NOARG = object()

# optional: reuse the parser’s symbol map if you export it
BINARY_SYMBOL_MAP = {
    "+": "ADD", "-": "SUBTRACT", "*": "MULTIPLY", "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE", "%": "MODULO", "**": "POWER",
    "<<": "LSHIFT", ">>": "RSHIFT", "|": "OR", "&": "AND",
    "^": "XOR", "@": "MATRIX_MULTIPLY",
}

class BasicOperation:
    def __init__(self, op_arg: Any, lineno: int):
        self.ops: list[Instr] = []
        self.lineno = lineno
        self.make_ops(op_arg)

    def _coerce_arg(self, op_name: str, arg: Any) -> Any:
        if op_name == "BINARY_OP":
            if isinstance(arg, str):
                name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
                return BinaryOp[name]
        return arg

    def add_op(self, op_name: str, op_arg=_NOARG):
        if op_arg is _NOARG:
            op = Instr(op_name, lineno=self.lineno)
        else:
            coerced = coerce_binary_op(op_arg) if op_name == "BINARY_OP" else op_arg
            op = Instr(op_name, coerced, lineno=self.lineno)
        self.ops.append(op)


    def make_ops(self, op_arg: Any):
        raise NotImplementedError


