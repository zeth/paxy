# paxy/ir.py
"""
Intermediate Representation (IR) for Paxy BASIC-like programs.

The parser does not emit Python bytecode instructions directly. Instead it
constructs a lightweight intermediate representation (IR) made up of simple
dataclasses:

    • Ident         - marks identifiers (variables, function names)
    • LabelDecl     - placeholder for a declared label (resolved in assembly)
    • JumpRef       - placeholder for a GO target
    • NamedJump     - placeholder for a conditional/unconditional jump
    • FuncDef       - placeholder for SUB … SBE blocks, capturing params/body
    • ReturnMarker  - placeholder for RET statements

This IR decouples parsing from assembly:

    - The parser only needs to recognize BASIC syntax and build IR nodes.
    - The assembler consumes IR nodes, resolves labels/jumps, rewrites locals
      vs globals, and finally lowers everything to concrete Python bytecode
      (`Instr` and `Label`).

`ParsedItem` is defined as the union of all possible IR node types plus
`Instr` itself. Both parser and assembler share this alias to make the flow
explicit: parser → IR → assembler → bytecode.
"""
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
    """Placeholder for a declared label like: LBL foo"""

    label_name: str
    lineno: int


@dataclass(frozen=True)
class JumpRef:
    """Placeholder for a goto-style reference like: GO foo"""

    target_name: str
    lineno: int


@dataclass(frozen=True)
class FuncDef:
    """
    Placeholder for SUB ... SBE.

    - name: function name
    - params: positional parameter names
    - body: parsed items of the function body (same item types as module-level)
    - lineno: source line where SUB was declared
    """

    name: str
    params: List[str]
    body: List["ParsedItem"]
    lineno: int


@dataclass(frozen=True)
class ReturnMarker:
    """
    Placeholder for RET inside a function body.

    - has_value: True if a value was pushed on the stack before RET
    - lineno: source line of RET
    """

    has_value: bool
    lineno: int


@dataclass(frozen=True)
class RangeBlock:
    var: str  # loop variable (identifier)
    start: object  # token already parsed (Ident or literal)
    end: object  # token already parsed (Ident or literal)
    body: list["ParsedItem"]
    lineno: int


ParsedItem = Union[
    Instr, NamedJump, LabelDecl, JumpRef, FuncDef, ReturnMarker, RangeBlock
]


COND_JUMP_OPS = {
    "POP_JUMP_IF_FALSE",
    "POP_JUMP_IF_TRUE",
    # "JUMP_IF_FALSE_OR_POP", "JUMP_IF_TRUE_OR_POP", ...
}
UNCOND_JUMP_FIXED = {"JUMP_FORWARD", "JUMP_BACKWARD"}  # explicit-direction jumps
