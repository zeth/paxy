# paxy/opcoerce.py
from bytecode import BinaryOp

BINARY_SYMBOL_MAP = {
    "+": "ADD", "-": "SUBTRACT", "*": "MULTIPLY", "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE", "%": "MODULO", "**": "POWER",
    "<<": "LSHIFT", ">>": "RSHIFT", "|": "OR", "&": "AND",
    "^": "XOR", "@": "MATRIX_MULTIPLY",
}

def coerce_binary_op(arg):
    if isinstance(arg, str):
        name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
        return BinaryOp[name]
    if isinstance(arg, int):
        return BinaryOp(arg)  # will raise if invalid
    return arg
