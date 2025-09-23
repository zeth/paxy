from bytecode import BinaryOp, Compare

BINARY_SYMBOL_MAP = {
    "+": "ADD",
    "-": "SUBTRACT",
    "*": "MULTIPLY",
    "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE",
    "%": "MODULO",
    "**": "POWER",
    "<<": "LSHIFT",
    ">>": "RSHIFT",
    "|": "OR",
    "&": "AND",
    "^": "XOR",
    "@": "MATRIX_MULTIPLY",
}

COMPARE_SYMBOL_MAP = {
    "==": "EQ",
    "!=": "NE",
    "<": "LT",
    "<=": "LE",
    ">": "GT",
    ">=": "GE",
    "in": "IN",
    "not in": "NOT_IN",
    "is": "IS",
    "is not": "IS_NOT",
    "exception match": "EXC_MATCH",
    "contains": "CONTAINS",
}

def coerce_binary_op(arg):
    if isinstance(arg, str):
        name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
        return BinaryOp[name]
    if isinstance(arg, int):
        return BinaryOp(arg)
    return arg

def coerce_compare_op(arg):
    if isinstance(arg, str):
        name = COMPARE_SYMBOL_MAP.get(arg, arg).upper().replace(" ", "_")
        return Compare[name]
    if isinstance(arg, int):
        return Compare(arg)
    return arg
