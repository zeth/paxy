from __future__ import annotations

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


CallableLoads = {"LOAD_GLOBAL", "LOAD_NAME", "LOAD_FAST", "LOAD_ATTR", "LOAD_DEREF"}


def _prev_instr_idx(seq: list[Union[Instr, Label, object]], start: int) -> int | None:
    j = start - 1
    while j >= 0:
        if isinstance(seq[j], Instr):
            return j
        j -= 1
    return None


def _next_instr_idx(seq: list[Union[Instr, Label, object]], start: int) -> int | None:
    j = start + 1
    while j < len(seq):
        if isinstance(seq[j], Instr):
            return j
        j += 1
    return None


def normalize_push_null_for_calls_312_seq(
    seq: list[Union[Instr, Label, object]],
) -> list[Union[Instr, Label, object]]:
    """
    For Python 3.12, canonicalize every CALL site to:

        ..., PUSH_NULL, <callable>, <arg1>.. <argN>, CALL n

    Also neutralize LOAD_GLOBAL's with-null flag on the callable and
    avoid touching unrelated PUSH_NULLs (especially when lineno=None).
    """
    if sys.version_info >= (3, 13):
        return list(seq)

    s = list(seq)
    i = 0
    while i < len(s):
        ins = s[i]
        if not isinstance(ins, Instr) or ins.name != "CALL":
            i += 1
            continue

        # 1) How many positional args?
        try:
            nargs = int(ins.arg or 0)
        except Exception:
            nargs = 0

        # 2) Backtrack over exactly 'nargs' argument pushes (skip labels & PUSH_NULL)
        cursor = i
        remaining = nargs
        while remaining:
            cursor = _prev_instr_idx(s, cursor)
            if cursor is None:
                break
            if isinstance(s[cursor], Instr) and s[cursor].name == "PUSH_NULL":
                # not an argument
                continue
            remaining -= 1
        if cursor is None or remaining:
            i += 1
            continue  # couldn't robustly locate args

        # 3) Find the callable: previous non-label, non-PUSH_NULL instruction
        callable_ix = _prev_instr_idx(s, cursor)
        while (
            callable_ix is not None
            and isinstance(s[callable_ix], Instr)
            and s[callable_ix].name == "PUSH_NULL"
        ):
            callable_ix = _prev_instr_idx(s, callable_ix)
        if callable_ix is None:
            i += 1
            continue

        callable_ins: Instr = s[callable_ix]  # type: ignore[assignment]

        # 3a) If it's LOAD_GLOBAL with (True, name), flip the flag to False
        if (
            callable_ins.name == "LOAD_GLOBAL"
            and isinstance(callable_ins.arg, tuple)
            and len(callable_ins.arg) == 2
            and isinstance(callable_ins.arg[0], bool)
            and callable_ins.arg[0] is True
        ):
            name = callable_ins.arg[1]
            callable_ins.arg = (False, name)

        # 3b) Remove PUSH_NULLs strictly between callable and CALL (those are always wrong)
        j = callable_ix + 1
        while j < i:
            if isinstance(s[j], Instr) and s[j].name == "PUSH_NULL":
                del s[j]
                if j < i:
                    i -= 1
                continue
            j += 1

        # 4) Ensure there is exactly one PUSH_NULL immediately before the callable.
        call_line = getattr(ins, "lineno", None)

        # Is there already one immediately before?
        has_immediate_null = (
            callable_ix - 1 >= 0
            and isinstance(s[callable_ix - 1], Instr)
            and s[callable_ix - 1].name == "PUSH_NULL"
        )

        if call_line is not None:
            # We can safely use same-line cleanup
            same_line_nulls = [
                j
                for j in range(i)  # strictly before CALL
                if isinstance(s[j], Instr)
                and s[j].name == "PUSH_NULL"
                and getattr(s[j], "lineno", None) == call_line
            ]

            if same_line_nulls:
                keep = same_line_nulls[-1]
                # Drop all other same-line NULLs
                for extra in reversed(same_line_nulls[:-1]):
                    del s[extra]
                    if extra < i:
                        i -= 1
                    if extra < callable_ix:
                        callable_ix -= 1

                # Move the kept one to sit right before the callable
                if keep != callable_ix - 1:
                    node = s.pop(keep)
                    if keep < i:
                        i -= 1
                    if keep < callable_ix:
                        callable_ix -= 1
                    insert_at = max(callable_ix, 0)
                    s.insert(insert_at, node)
                    if insert_at <= i:
                        i += 1
                    callable_ix += 1  # callable shifted right
        else:
            # No reliable line info: be conservative.
            # Only insert a NULL if there isn't an immediate one already.
            if not has_immediate_null:
                ln = getattr(callable_ins, "lineno", None)
                s.insert(callable_ix, Instr("PUSH_NULL", lineno=ln))
                if callable_ix <= i:
                    i += 1
                callable_ix += 1

        # Final belt-and-braces: if there’s still no immediate NULL, insert one now.
        has_immediate_null = (
            callable_ix - 1 >= 0
            and isinstance(s[callable_ix - 1], Instr)
            and s[callable_ix - 1].name == "PUSH_NULL"
        )
        if not has_immediate_null:
            ln = getattr(callable_ins, "lineno", None) or getattr(ins, "lineno", None)
            s.insert(callable_ix, Instr("PUSH_NULL", lineno=ln))
            if callable_ix <= i:
                i += 1
            callable_ix += 1

        i += 1

    return s
