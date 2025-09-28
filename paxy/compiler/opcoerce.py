from __future__ import annotations

from typing import Any
from enum import IntEnum
from bytecode import BinaryOp
from bytecode.instr import Compare


class IsOp(IntEnum):
    IS = 0
    IS_NOT = 1


class ContainsOp(IntEnum):
    IN = 0
    NOT_IN = 1


BINARY_SYMBOL_MAP: dict[str, str] = {
    "+": "ADD",
    "-": "SUBTRACT",
    "*": "MULTIPLY",
    "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE",
    "%": "REMAINDER",
    "**": "POWER",
    "<<": "LSHIFT",
    ">>": "RSHIFT",
    "|": "OR",
    "&": "AND",
    "^": "XOR",
    "@": "MATRIX_MULTIPLY",
}

COMPARE_SYMBOL_MAP: dict[str, str] = {
    "==": "EQ",
    "!=": "NE",
    "<": "LT",
    "<=": "LE",
    ">": "GT",
    ">=": "GE",
}

IS_SYMBOL_MAP: dict[str, str] = {
    "is": "IS",
    "is not": "IS_NOT",
}

CONTAINS_SYMBOL_MAP: dict[str, str] = {
    "in": "IN",
    "not in": "NOT_IN",
}


def coerce_binary_op(arg: Any) -> BinaryOp:
    """
    Accept BinaryOp | str(symbol|name) | int -> BinaryOp
    """
    if isinstance(arg, BinaryOp):
        return arg

    if isinstance(arg, str):
        name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
        try:
            return BinaryOp[name]  # Enum name lookup
        except Exception as e:
            raise SyntaxError(
                f"Unknown BINARY_OP name/symbol {name!r} (from {arg!r})"
            ) from e

    if isinstance(arg, int):
        try:
            return BinaryOp(arg)  # Enum value lookup
        except Exception as e:
            raise SyntaxError(f"Invalid BINARY_OP code {arg}") from e

    raise SyntaxError("BINARY_OP expects a symbol/name or int")


def coerce_compare_op(arg: Any) -> Compare:
    """
    Accept Compare | str(symbol|name) | int -> Compare
    Only EQ/NE/LT/LE/GT/GE belong here in Python 3.13.
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


def coerce_is_op(arg: Any) -> IsOp:
    """
    Accept IsOp | str(name/symbol) | int -> IsOp
    """
    if isinstance(arg, IsOp):
        return arg

    if isinstance(arg, str):
        name = IS_SYMBOL_MAP.get(arg, arg).upper()
        try:
            return IsOp[name]
        except Exception as e:
            raise SyntaxError(
                f"Unknown IS_OP name/symbol {name!r} (from {arg!r})"
            ) from e

    if isinstance(arg, int):
        try:
            return IsOp(arg)
        except Exception as e:
            raise SyntaxError(f"Invalid IS_OP code {arg}") from e

    raise SyntaxError("IS_OP expects a symbol/name or int")


def coerce_contains_op(arg: Any) -> ContainsOp:
    """
    Accept ContainsOp | str(name/symbol) | int -> ContainsOp
    """
    if isinstance(arg, ContainsOp):
        return arg

    if isinstance(arg, str):
        name = CONTAINS_SYMBOL_MAP.get(arg, arg).upper()
        try:
            return ContainsOp[name]
        except Exception as e:
            raise SyntaxError(
                f"Unknown CONTAINS_OP name/symbol {name!r} (from {arg!r})"
            ) from e

    if isinstance(arg, int):
        try:
            return ContainsOp(arg)
        except Exception as e:
            raise SyntaxError(f"Invalid CONTAINS_OP code {arg}") from e

    raise SyntaxError("CONTAINS_OP expects a symbol/name or int")
