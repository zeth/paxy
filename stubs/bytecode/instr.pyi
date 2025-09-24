# stubs/bytecode/instr.pyi
from enum import Enum

class Compare(Enum):
    EQ: "Compare"
    NE: "Compare"
    LT: "Compare"
    LE: "Compare"
    GT: "Compare"
    GE: "Compare"
