from __future__ import annotations

from typing import Any, Mapping, Iterable, Sequence, overload
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

opmap: Mapping[str, int]

class CompilerFlags(IntFlag):
    NOFREE: CompilerFlags
    OPTIMIZED: CompilerFlags
    NEWLOCALS: CompilerFlags

class Bytecode(Sequence[Instr]):
    # Attributes used by your assembler
    name: str
    argcount: int
    argnames: list[str]
    filename: str
    flags: CompilerFlags | int
    first_lineno: int

    def __init__(self, instrs: Sequence[Instr | Label] | None = ...) -> None: ...
    def to_code(self) -> CodeType: ...

    # Minimal Sequence/Mutation surface you likely use
    def append(self, instr: Instr) -> None: ...
    def extend(self, instrs: Iterable[Instr]) -> None: ...
    def __len__(self) -> int: ...
    @overload
    def __getitem__(self, i: int) -> Instr: ...
    @overload
    def __getitem__(self, s: slice) -> list[Instr]: ...
