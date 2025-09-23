from __future__ import annotations
from dataclasses import dataclass
from bytecode import Instr


@dataclass(frozen=True)
class LabelDecl:
    name: str
    lineno: int


@dataclass(frozen=True)
class JumpRef:
    name: str
    lineno: int


# # NEW: placeholder for native jumps that name a label, e.g. POP_JUMP_IF_FALSE end
# @dataclass(frozen=True)
# class NamedJump:
#     opcode: str
#     target: str
#     lineno: int


class NamedJump(Instr):
    """
    Placeholder for native jumps that reference a label by *name*.
    Behaves like an Instr so it fits list[Instr], but carries the
    unresolved target string for a later resolution pass.
    """

    def __init__(self, opcode: str, target: str, lineno: int):
        # For bytecode.Instr, 'name' is the opcode and 'arg' is the target.
        # Passing the string target is fine; your resolver can replace it with a Label later.
        super().__init__(opcode, target, lineno=lineno)
        # Optional: keep an explicit field if you want, though .arg already holds it.
        self.target_name = target
        self.is_named_jump = True  # handy flag for resolvers
