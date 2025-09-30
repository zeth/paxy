# paxy/basic/base.py

from typing import Any, TypeAlias, Union
from bytecode import Instr, BinaryOp
from paxy.compiler.opcoerce import coerce_binary_op
from paxy.compiler.ir import ReturnMarker, LabelDecl, JumpRef, NamedJump

_NOARG = object()

# Names should match bytecode's BinaryOp (3.12/3.13)
BINARY_SYMBOL_MAP: dict[str, str] = {
    "+": "ADD",
    "-": "SUBTRACT",
    "*": "MULTIPLY",
    "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE",
    "%": "REMAINDER",
    "**": "POWER",
    "<<": "LSHIFT",
    ">>": "RSHIFT",
    "|": "OR",
    "&": "AND",
    "^": "XOR",
    "@": "MATRIX_MULTIPLY",
}

# What BASIC ops may emit
BasicItem = Union[Instr, LabelDecl, JumpRef, NamedJump, ReturnMarker]


class Command:

    COMMAND = "COMMAND"
    SUMMARY = "Base command, override and add description in subclass."

    def __init__(self, op_args: list[Any], lineno: int) -> None:
        self.ops: list[BasicItem] = []
        self.lineno: int = lineno
        self.make_ops(op_args)

    def _coerce_arg(self, op_name: str, arg: Any) -> Any:
        if op_name == "BINARY_OP" and isinstance(arg, str):
            name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
            return BinaryOp[name]
        return arg

    def add_op(self, op_name: str, op_arg: Any = _NOARG) -> None:
        if op_arg is _NOARG:
            op = Instr(op_name, lineno=self.lineno)
        else:
            coerced = coerce_binary_op(op_arg) if op_name == "BINARY_OP" else op_arg
            op = Instr(op_name, coerced, lineno=self.lineno)
        self.ops.append(op)

    def make_ops(self, op_args: list[Any]) -> None:
        raise NotImplementedError

    def _emit_load_for(self, value: Any) -> None:
        from paxy.compiler.ir import Ident

        if isinstance(value, Ident):
            self.add_op("LOAD_NAME", str(value))
        else:
            self.add_op("LOAD_CONST", value)


CommandMap: TypeAlias = dict[str, type[Command]]
