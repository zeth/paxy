# paxy/funcplace.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Union, Any

# We only use Instr for typing clarity; other placeholders are opaque here (Any).
from bytecode import Instr

ParsedItem = Union[
    Instr, Any
]  # Other placeholders (LabelDecl, JumpRef, NamedJump, ...) are allowed


@dataclass(frozen=True)
class FuncDef:
    """
    Placeholder for SUB ... SUBEND.

    - name: function name
    - params: positional parameter names
    - body: parsed items of the function body (same item types as module-level)
    - lineno: source line where SUB was declared
    """

    name: str
    params: List[str]
    body: List[ParsedItem]
    lineno: int


@dataclass(frozen=True)
class ReturnMarker:
    """
    Placeholder for RETURN inside a function body.

    - has_value: True if a value was pushed on the stack before RETURN
    - lineno: source line of RETURN
    """

    has_value: bool
    lineno: int
