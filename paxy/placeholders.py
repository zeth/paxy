# paxy/placeholders.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Union
from bytecode import Instr


class Ident(str):
    """Marker type for identifiers (NAME tokens). Subclass of str so equality stays normal."""

    pass


@dataclass(frozen=True)
class NamedJump:
    """Placeholder for a native jump with a named target."""

    opcode: str
    target_name: str
    lineno: int


@dataclass(frozen=True)
class LabelDecl:
    """Placeholder for a declared label like: LABEL foo"""

    label_name: str
    lineno: int


@dataclass(frozen=True)
class JumpRef:
    """Placeholder for a goto-style reference like: GOTO foo"""

    target_name: str
    lineno: int


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


ParsedItem = Union[Instr, NamedJump, LabelDecl, JumpRef, FuncDef, ReturnMarker]
