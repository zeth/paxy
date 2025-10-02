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
    if sys.version_info >= (3, 13):
        return list(seq)

    s = list(seq)
    i = 0
    while i < len(s):
        ins = s[i]
        if not isinstance(ins, Instr) or ins.name != "CALL":
            i += 1
            continue

        # arg count
        try:
            nargs = int(ins.arg or 0)
        except Exception:
            nargs = 0

        # find the nearest LOAD_* before CALL (label-aware, robust)
        callable_ix: int | None = None
        steps_left = max(nargs + 3, 4)
        cursor = i
        while steps_left:
            # walk to previous *instruction*
            cursor = cursor - 1
            while cursor >= 0 and not isinstance(s[cursor], Instr):
                cursor -= 1
            if cursor < 0:
                break
            steps_left -= 1
            obj = s[cursor]
            if isinstance(obj, Instr) and obj.name in {
                "LOAD_GLOBAL",
                "LOAD_NAME",
                "LOAD_FAST",
                "LOAD_ATTR",
                "LOAD_DEREF",
            }:
                callable_ix = cursor
                break

        if callable_ix is None:
            i += 1
            continue

        callable_ins: Instr = s[callable_ix]  # type: ignore[assignment]

        # NEW: if LOAD_GLOBAL has the with-NULL flag set, clear it (3.12 only).
        if (
            callable_ins.name == "LOAD_GLOBAL"
            and isinstance(callable_ins.arg, tuple)
            and len(callable_ins.arg) == 2
            and isinstance(callable_ins.arg[0], bool)
            and callable_ins.arg[0] is True
        ):
            name = callable_ins.arg[1]
            callable_ins.arg = (False, name)

        # Build instruction-only window from callable .. before CALL
        win_idxs: list[int] = []
        j = callable_ix
        while True:
            win_idxs.append(j)
            k = j + 1
            while k < len(s) and not isinstance(s[k], Instr):
                k += 1
            if k >= i:
                break
            j = k

        # Ensure exactly one PUSH_NULL immediately *before* the callable
        nulls = [
            ix
            for ix in win_idxs
            if isinstance(s[ix], Instr) and s[ix].name == "PUSH_NULL"
        ]

        if not nulls:
            ln = getattr(callable_ins, "lineno", None) or getattr(ins, "lineno", None)
            s.insert(callable_ix, Instr("PUSH_NULL", lineno=ln))
            i += 1
        else:
            keep = nulls[0]
            # remove extras
            for extra in reversed(nulls[1:]):
                del s[extra]
                if extra < i:
                    i -= 1
            # move the kept NULL to just before callable
            if keep != callable_ix - 1:
                node = s.pop(keep)
                if keep < callable_ix:
                    callable_ix -= 1
                s.insert(max(callable_ix - 1, 0), node)
                if keep < i:
                    i -= 1

        # --- NEW: remove any stray PUSH_NULL earlier on the SAME source line as this CALL.
        # In your failing case, a NULL from line 2 leaked before a prior STORE_NAME on line 1.
        # We keep the one at (callable_ix - 1) and delete any other PUSH_NULL with the same lineno.
        call_line = getattr(ins, "lineno", None)
        j = callable_ix - 2  # start one before the kept NULL
        while j >= 0:
            obj = s[j]
            if (
                isinstance(obj, Instr)
                and obj.name == "PUSH_NULL"
                and getattr(obj, "lineno", None) == call_line
            ):
                del s[j]
                if j < i:
                    i -= 1  # keep CALL index accurate
                if j < callable_ix:
                    callable_ix -= 1  # callable shifts left if we removed before it
            j -= 1

        i += 1

    return s
