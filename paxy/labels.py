# paxy/labels.py
from __future__ import annotations
from bytecode import Instr


class NamedJump(Instr):
    """
    Placeholder for native jumps that reference a label by *name*.
    Fits list[Instr] but carries an unresolved target to be resolved later.
    """

    def __init__(self, opcode: str, target: str, lineno: int):
        super().__init__(opcode, target, lineno=lineno)
        self.target_name = target
        self.is_named_jump = True

    # Properties expected by assembler:
    @property
    def opcode(self) -> str:  # semantic opcode
        return str(self.name)

    @property
    def target(self) -> str:  # semantic target label name
        return str(self.arg)


class LabelDecl(Instr):
    """
    Placeholder for a declared label (e.g. 'LABEL foo').
    The assembler will replace this with a concrete bytecode.Label and
    remove or rewrite this placeholder during resolution.
    """

    def __init__(self, name: str, lineno: int):
        # Use a synthetic opcode name so downstream passes can spot it.
        super().__init__("LABEL_DECL", name, lineno=lineno)
        self.label_name = name
        self.is_label_decl = True


class JumpRef(Instr):
    """
    Placeholder for a goto-style reference to a label name (e.g. 'GOTO foo').
    The assembler will pick the appropriate concrete jump opcode and patch
    the arg to a real Label.
    """

    def __init__(self, target: str, lineno: int):
        super().__init__("JUMP_REF", target, lineno=lineno)
        self.target_name = target
        self.is_jump_ref = True
