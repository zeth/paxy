from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class LabelDecl:
    name: str
    lineno: int

@dataclass(frozen=True)
class JumpRef:
    name: str
    lineno: int

# NEW: placeholder for native jumps that name a label, e.g. POP_JUMP_IF_FALSE end
@dataclass(frozen=True)
class NamedJump:
    opcode: str
    target: str
    lineno: int
