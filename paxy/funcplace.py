# paxy/funcplace.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence, Union, Any

# Import the same ParsedItem type you use in the parser/assembler pipeline.
# If you keep this module import-light, import by string or adjust as needed.
from bytecode import Instr, Label  # only for typing clarity; not used at runtime


# ParsedItem in your project currently includes: Instr | LabelDecl | JumpRef | NamedJump
# We'll re-declare a local alias to avoid circulars in type-checkers.
ParsedItem = Union[
    Instr, Any
]  # "Any" stands in for your other placeholders (LabelDecl, JumpRef, NamedJump)


@dataclass(frozen=True)
class FuncDef:
    """
    Placeholder for a function (SUB … SUBEND).
    The parser (or a BASIC op) should produce one of these with a body parsed
    into ParsedItem entries. The assembler lowers it to:
      LOAD_CONST <code>
      MAKE_FUNCTION 0
      STORE_NAME <name>
    """

    name: str
    params: List[str]
    body: List[ParsedItem]
    lineno: int


@dataclass(frozen=True)
class ReturnMarker:
    """
    Placeholder for RETURN inside a function body.
    If has_value is False -> RETURN_CONST None (3.13: RETURN_CONST 0)
    If has_value is True  -> assumes value is already on the stack, emits RETURN_VALUE.
    """

    has_value: bool
    lineno: int
