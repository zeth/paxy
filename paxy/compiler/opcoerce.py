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
    Python 3.12 requires (ignoring labels):
        ..., PUSH_NULL, <callable>, <arg1>.. <argN>, CALL n
    For each CALL (3.12 only), enforce that shape by:
      • swapping (callable, PUSH_NULL) → (PUSH_NULL, callable)
      • inserting PUSH_NULL immediately *before* the callable if it's missing
    """
    if sys.version_info >= (3, 13):
        return list(seq)

    s: list[Union[Instr, Label, object]] = list(seq)

    def is_instr(ix: int) -> bool:
        return 0 <= ix < len(s) and isinstance(s[ix], Instr)

    def prev_instr_idx(ix: int) -> int | None:
        j = ix - 1
        while j >= 0:
            if isinstance(s[j], Instr):
                return j
            j -= 1
        return None

    def next_instr_idx(ix: int) -> int | None:
        j = ix + 1
        while j < len(s):
            if isinstance(s[j], Instr):
                return j
            j += 1
        return None

    def is_callable_load(obj: object) -> bool:
        return isinstance(obj, Instr) and obj.name in {
            "LOAD_GLOBAL",
            "LOAD_NAME",
            "LOAD_FAST",
            "LOAD_ATTR",
            "LOAD_DEREF",
        }

    i = 0
    while i < len(s):
        if not is_instr(i):
            i += 1
            continue

        call_ins = s[i]  # type: ignore[assignment]
        if isinstance(call_ins, Instr) and call_ins.name == "CALL":
            # Walk backwards over *instructions only* to find the callable:
            try:
                nargs = int(call_ins.arg or 0)
            except Exception:
                nargs = 0

            # Step back over argN..arg1 and then the callable (nargs + 1 instructions)
            steps = nargs + 1
            j = i
            while steps and (j := prev_instr_idx(j)) is not None:
                steps -= 1
            if steps or j is None:
                i += 1
                continue  # couldn't find callable robustly

            callable_ix = j
            callable_ins = s[callable_ix]  # type: ignore[assignment]
            if not is_callable_load(callable_ins):
                i += 1
                continue  # not a simple LOAD_* callable; leave it alone

            # Find immediate previous / next *instruction* neighbors of the callable
            prev_ix = prev_instr_idx(callable_ix)
            next_ix = next_instr_idx(callable_ix)

            # If we have (callable, PUSH_NULL) → swap them
            if next_ix is not None:
                next_ins = s[next_ix]
                if isinstance(next_ins, Instr) and next_ins.name == "PUSH_NULL":
                    s[callable_ix], s[next_ix] = next_ins, callable_ins
                    # CALL index unaffected in terms of *instruction* neighbors
                    i += 1
                    continue

            # Already correct if previous instr is PUSH_NULL
            if prev_ix is not None:
                prev_ins = s[prev_ix]
                if isinstance(prev_ins, Instr) and prev_ins.name == "PUSH_NULL":
                    i += 1
                    continue

            # Otherwise, insert PUSH_NULL immediately *before* the callable
            ln = getattr(callable_ins, "lineno", None) or getattr(
                call_ins, "lineno", None
            )
            s.insert(callable_ix, Instr("PUSH_NULL", lineno=ln))
            # Inserting before the callable shifts CALL one slot to the right overall;
            # bump i so we don't reprocess the same CALL.
            i += 1
        else:
            i += 1

    return s
