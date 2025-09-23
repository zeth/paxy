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


def _bad_type(expected: str, got: object) -> SyntaxError:
    return SyntaxError(f"{expected}, got {type(got).__name__}: {got!r}")


def coerce_binary_op(arg):
    """
    Accepts:
      - symbol: "+", "-", "*", ...
      - enum name (case-insensitive): "ADD", "subtract", ...
      - int code
      - BinaryOp (pass-through)

    Raises SyntaxError with a clear message otherwise.
    """
    if isinstance(arg, BinaryOp):
        return arg

    if isinstance(arg, str):
        # map common symbols to enum names first
        name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
        try:
            return BinaryOp[name]
        except KeyError:
            raise SyntaxError(
                f"Unknown BINARY_OP name/symbol {arg!r} "
                f"(after normalization: {name!r})"
            )

    if isinstance(arg, int):
        try:
            return BinaryOp(arg)
        except Exception:
            raise SyntaxError(f"Invalid BINARY_OP code {arg}")

    raise _bad_type("BINARY_OP expects a symbol/name or int", arg)


def coerce_compare_op(arg):
    """
    Accepts:
      - symbol/phrase: '==', '!=', '<=', 'in', 'not in', 'is', 'is not', ...
      - enum name (case-insensitive): 'EQ', 'NOT_IN', ...
      - int code
      - Compare (pass-through)

    Raises SyntaxError with a clear message otherwise.
    """
    if isinstance(arg, Compare):
        return arg

    if isinstance(arg, str):
        # normalize phrases like "not in" -> "NOT_IN"
        name = COMPARE_SYMBOL_MAP.get(arg, arg).upper().replace(" ", "_")
        try:
            return Compare[name]
        except KeyError:
            raise SyntaxError(
                f"Unknown COMPARE_OP name/symbol {arg!r} "
                f"(after normalization: {name!r})"
            )

    if isinstance(arg, int):
        try:
            return Compare(arg)
        except Exception:
            raise SyntaxError(f"Invalid COMPARE_OP code {arg}")

    raise _bad_type("COMPARE_OP expects a symbol/name or int", arg)
