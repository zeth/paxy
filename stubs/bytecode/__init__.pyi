from __future__ import annotations

from typing import Any, Mapping, Iterable, Sequence, overload
from typing import MutableSequence, Iterator, Union, Sequence, Optional
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

Item = Union[Instr, Label]

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

class Bytecode(MutableSequence[Item]):
    # Attributes used by your assembler
    name: str
    argcount: int
    argnames: list[str]
    filename: str
    flags: CompilerFlags | int
    first_lineno: int

    def __init__(self, seq: Optional[Sequence[Item]] = ...) -> None: ...
    def to_code(self) -> CodeType: ...

    # Element access
    @overload
    def __getitem__(self, index: int) -> Item: ...
    @overload
    def __getitem__(self, index: slice) -> list[Item]: ...
    @overload
    def __setitem__(self, index: int, value: Item) -> None: ...
    @overload
    def __setitem__(self, index: slice, value: Iterable[Item]) -> None: ...
    def __delitem__(self, index: int | slice) -> None: ...
    def insert(self, index: int, value: Item) -> None: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[Item]: ...  # or omit to inherit

    # IMPORTANT:
    # Do NOT widen these. Either omit them (inherit from MutableSequence)
    # or keep them EXACTLY as Item / Iterable[Item].
    def append(self, value: Item) -> None: ...
    def extend(self, values: Iterable[Item]) -> None: ...
