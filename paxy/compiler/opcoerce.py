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
    """For Python 3.12, canonicalize every CALL site to:
      ..., PUSH_NULL, <callable>, <arg1>.. <argN>, CALL n
    Also neutralize LOAD_GLOBAL’s with-null flag on the callable
    and remove stray same-line PUSH_NULLs earlier on the line.
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

        # 1) Get positional arg count
        try:
            nargs = int(ins.arg or 0)
        except Exception:
            nargs = 0

        # 2) Walk back over exactly 'nargs' ARG pushes (skip labels and PUSH_NULL)
        cursor = i
        remaining = nargs
        while remaining:
            cursor = _prev_instr_idx(s, cursor)
            if cursor is None:
                break
            if isinstance(s[cursor], Instr) and s[cursor].name == "PUSH_NULL":
                # not an argument; ignore
                continue
            remaining -= 1
        if cursor is None or remaining:
            i += 1
            continue  # couldn't robustly locate args

        # 3) The callable is the previous non-label, non-PUSH_NULL instruction
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

        # 3a) If it's a LOAD_GLOBAL with with-null flag set, turn it off
        if (
            callable_ins.name == "LOAD_GLOBAL"
            and isinstance(callable_ins.arg, tuple)
            and len(callable_ins.arg) == 2
            and isinstance(callable_ins.arg[0], bool)
            and callable_ins.arg[0] is True
        ):
            name = callable_ins.arg[1]
            callable_ins.arg = (False, name)

        # 4) Ensure exactly one PUSH_NULL on this source line,
        #    positioned immediately before the callable.

        call_line = getattr(ins, "lineno", None)

        # Find all PUSH_NULLs on the *same* line as the CALL that occur before CALL
        same_line_nulls = [
            j
            for j in range(i)  # strictly before CALL
            if isinstance(s[j], Instr)
            and s[j].name == "PUSH_NULL"
            and getattr(s[j], "lineno", None) == call_line
        ]

        if same_line_nulls:
            # Keep the one closest to CALL; drop the rest
            keep = same_line_nulls[-1]

            # Remove extras (descending so indices stay valid)
            for extra in reversed(same_line_nulls[:-1]):
                del s[extra]
                if extra < i:
                    i -= 1
                if extra < callable_ix:
                    callable_ix -= 1

            # Move the kept one to be immediately before the callable
            if keep != callable_ix - 1:
                node = s.pop(keep)
                # adjust indices after pop
                if keep < i:
                    i -= 1
                if keep < callable_ix:
                    callable_ix -= 1

                # Insert AT callable_ix so it lands just before it post-insert
                insert_at = max(callable_ix, 0)
                s.insert(insert_at, node)
                if insert_at <= i:
                    i += 1
                callable_ix += 1  # callable shifted right by the insert

        else:
            # No same-line NULL exists: insert one right before callable
            ln = getattr(callable_ins, "lineno", None) or call_line
            s.insert(callable_ix, Instr("PUSH_NULL", lineno=ln))
            if callable_ix <= i:
                i += 1
            callable_ix += 1

        # Belt-and-braces: if any other same-line NULLs remain before CALL and
        # are not immediately before the callable, remove them.
        j = 0
        while j < i:
            if (
                isinstance(s[j], Instr)
                and s[j].name == "PUSH_NULL"
                and getattr(s[j], "lineno", None) == call_line
                and j != (callable_ix - 1)
            ):
                del s[j]
                if j < i:
                    i -= 1
                if j < callable_ix:
                    callable_ix -= 1
                continue
            j += 1

        i += 1

    return s
