# paxy/opcoerce.py
from __future__ import annotations

from bytecode import BinaryOp
from bytecode.instr import Compare


# Maps text symbols to BinaryOp enum names (3.13)
BINARY_SYMBOL_MAP = {
    "+": "ADD",
    "-": "SUBTRACT",
    "*": "MULTIPLY",
    "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE",
    "%": "REMAINDER",  # 3.13 enum name
    "**": "POWER",
    "<<": "LSHIFT",
    ">>": "RSHIFT",
    "|": "OR",
    "&": "AND",
    "^": "XOR",
    "@": "MATRIX_MULTIPLY",
}

# Maps textual compare operators to Compare enum names (3.13)
COMPARE_SYMBOL_MAP = {
    "==": "EQ",
    "!=": "NE",
    "<": "LT",
    "<=": "LE",
    ">": "GT",
    ">=": "GE",
    "in": "IN_OP",
    "not in": "NOT_IN_OP",
    "is": "IS_OP",
    "is not": "IS_NOT_OP",
    "exception match": "EXC_MATCH",
    "contains": "CONTAINS_OP",
}


def coerce_binary_op(arg):
    """
    Accept:
      - BinaryOp member -> pass through
      - str: symbol or name (case-insensitive) -> BinaryOp[name]
      - int: underlying enum value -> BinaryOp(value)
    Raise SyntaxError with helpful messages otherwise.
    """
    if isinstance(arg, BinaryOp):
        return arg

    if isinstance(arg, str):
        name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
        try:
            return BinaryOp[name]
        except Exception as e:
            raise SyntaxError(
                f"Unknown BINARY_OP name/symbol {name!r} (from {arg!r})"
            ) from e

    if isinstance(arg, int):
        try:
            return BinaryOp(arg)
        except Exception as e:
            raise SyntaxError(f"Invalid BINARY_OP code {arg}") from e

    raise SyntaxError("BINARY_OP expects a symbol/name or int")


def coerce_compare_op(arg):
    """
    Accept:
      - Compare member -> pass through
      - str: symbol or name (case-insensitive) -> Compare[name]
      - int: underlying enum value -> Compare(value)
    Raise SyntaxError with helpful messages otherwise.
    """
    if isinstance(arg, Compare):
        return arg

    if isinstance(arg, str):
        name = COMPARE_SYMBOL_MAP.get(arg, arg).upper()
        try:
            return Compare[name]
        except Exception as e:
            raise SyntaxError(
                f"Unknown COMPARE_OP name/symbol {name!r} (from {arg!r})"
            ) from e

    if isinstance(arg, int):
        try:
            return Compare(arg)
        except Exception as e:
            raise SyntaxError(f"Invalid COMPARE_OP code {arg}") from e

    raise SyntaxError("COMPARE_OP expects a symbol/name or int")
