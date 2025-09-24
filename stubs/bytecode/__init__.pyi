from typing import Any, Mapping, Iterable, Sequence
from types import CodeType
from enum import Enum, IntFlag

class Label: ...
class CellVar: ...
class FreeVar: ...

class Instr:
    name: str
    arg: Any
    lineno: int
    def __init__(
        self, name: str, arg: Any | None = ..., *, lineno: int | None = ...
    ) -> None: ...

class BinaryOp(Enum):
    ADD: "BinaryOp"
    SUBTRACT: "BinaryOp"
    MULTIPLY: "BinaryOp"
    TRUE_DIVIDE: "BinaryOp"
    FLOOR_DIVIDE: "BinaryOp"
    REMAINDER: "BinaryOp"
    POWER: "BinaryOp"
    LSHIFT: "BinaryOp"
    RSHIFT: "BinaryOp"
    OR: "BinaryOp"
    AND: "BinaryOp"
    XOR: "BinaryOp"
    MATRIX_MULTIPLY: "BinaryOp"

class Compare(Enum):
    EQ: "Compare"
    NE: "Compare"
    LT: "Compare"
    LE: "Compare"
    GT: "Compare"
    GE: "Compare"

class Bytecode:
    filename: str
    name: str
    flags: int
    first_lineno: int
    def __init__(self, instrs: Sequence[Instr | Label] | None = ...) -> None: ...
    def to_code(self) -> CodeType: ...

class CompilerFlags(IntFlag):
    NOFREE: int

opmap: Mapping[str, int]
