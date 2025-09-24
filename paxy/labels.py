# paxy/labels.py
from __future__ import annotations
from dataclasses import dataclass


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
