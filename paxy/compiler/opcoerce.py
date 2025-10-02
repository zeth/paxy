import sys
from typing import Any, Union
from enum import IntEnum
from bytecode import BinaryOp, Instr, Label
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


def normalize_push_null_for_calls_312_seq(
    seq: list[Union[Instr, Label, object]],
) -> list[Union[Instr, Label, object]]:
    """
    Python 3.12 requires:
        ..., PUSH_NULL, <callable>, <arg1>.. <argN>, CALL N
    For each CALL (3.12 only), enforce that shape by:
      • swapping (callable, PUSH_NULL) → (PUSH_NULL, callable)
      • inserting PUSH_NULL if missing
    """
    if sys.version_info >= (3, 13):
        return list(seq)

    s: list[Union[Instr, Label, object]] = list(seq)

    def is_callable_load(x: object) -> bool:
        return isinstance(x, Instr) and x.name in {
            "LOAD_NAME",
            "LOAD_GLOBAL",
            "LOAD_FAST",
            "LOAD_ATTR",
            "LOAD_DEREF",
        }

    i = 0
    while i < len(s):
        ins = s[i]
        if isinstance(ins, Instr) and ins.name == "CALL":
            try:
                nargs = int(ins.arg or 0)
            except Exception:
                nargs = 0

            # Positions just before CALL:
            #   a_idx = i - (nargs + 2)   # either callable or PUSH_NULL
            #   b_idx = i - (nargs + 1)   # either PUSH_NULL, callable, or first arg
            a_idx = i - (nargs + 2)
            b_idx = i - (nargs + 1)

            if 0 <= a_idx < len(s) and 0 <= b_idx < len(s):
                a = s[a_idx]
                b = s[b_idx]

                # (callable, PUSH_NULL, args)  → swap
                if (
                    is_callable_load(a)
                    and isinstance(b, Instr)
                    and b.name == "PUSH_NULL"
                ):
                    s[a_idx], s[b_idx] = b, a

                # (PUSH_NULL, callable, args) → already correct
                elif (
                    isinstance(a, Instr)
                    and a.name == "PUSH_NULL"
                    and is_callable_load(b)
                ):
                    pass

                # ( ?, callable, args ) → missing PUSH_NULL before callable → insert at a_idx
                elif is_callable_load(b) and not (
                    isinstance(a, Instr) and a.name == "PUSH_NULL"
                ):
                    ln = getattr(b, "lineno", None) or getattr(ins, "lineno", None)
                    s.insert(a_idx, Instr("PUSH_NULL", lineno=ln))
                    i += 1  # CALL shifted by insert

                # ( callable, ?, args ) → missing PUSH_NULL after a callable → insert before callable
                elif is_callable_load(a) and not (
                    isinstance(b, Instr) and b.name == "PUSH_NULL"
                ):
                    ln = getattr(a, "lineno", None) or getattr(ins, "lineno", None)
                    s.insert(a_idx, Instr("PUSH_NULL", lineno=ln))
                    i += 1  # CALL shifted by insert
        i += 1

    return s
