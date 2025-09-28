import pytest
from bytecode import BinaryOp
from bytecode.instr import Compare

# Import identity/membership enums from our module so tests don't depend on
# whether the bytecode package exposes them.
from paxy.compiler.opcoerce import (
    coerce_binary_op,
    coerce_compare_op,
    coerce_is_op,
    coerce_contains_op,
    IsOp,
    ContainsOp,
)


# -----------------------------
# coerce_binary_op
# -----------------------------


def test_binary_pass_through():
    x = coerce_binary_op(BinaryOp.ADD)
    assert x is BinaryOp.ADD


@pytest.mark.parametrize(
    "text, expected",
    [
        ("+", BinaryOp.ADD),
        ("-", BinaryOp.SUBTRACT),
        ("*", BinaryOp.MULTIPLY),
        ("/", BinaryOp.TRUE_DIVIDE),
        ("//", BinaryOp.FLOOR_DIVIDE),
        ("%", BinaryOp.REMAINDER),
        ("**", BinaryOp.POWER),
        ("<<", BinaryOp.LSHIFT),
        (">>", BinaryOp.RSHIFT),
        ("|", BinaryOp.OR),
        ("&", BinaryOp.AND),
        ("^", BinaryOp.XOR),
        ("@", BinaryOp.MATRIX_MULTIPLY),
    ],
)
def test_binary_symbol_mapping(text, expected):
    assert coerce_binary_op(text) is expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("add", BinaryOp.ADD),
        ("SUBTRACT", BinaryOp.SUBTRACT),
        ("mUlTiPlY", BinaryOp.MULTIPLY),
    ],
)
def test_binary_name_case_insensitive(name, expected):
    assert coerce_binary_op(name) is expected


def test_binary_int_code_valid():
    code = BinaryOp.ADD.value
    assert coerce_binary_op(code) is BinaryOp.ADD


def test_binary_int_code_invalid():
    with pytest.raises(SyntaxError) as exc:
        coerce_binary_op(999_999)
    assert "Invalid BINARY_OP code" in str(exc.value)


def test_binary_unknown_name():
    with pytest.raises(SyntaxError) as exc:
        coerce_binary_op("not_an_op")
    s = str(exc.value)
    assert "Unknown BINARY_OP name/symbol" in s
    assert "NOT_AN_OP" in s


def test_binary_bad_type():
    with pytest.raises(SyntaxError) as exc:
        coerce_binary_op(3.14)
    assert "BINARY_OP expects a symbol/name or int" in str(exc.value)


# -----------------------------
# coerce_compare_op
# -----------------------------


def test_compare_pass_through():
    x = coerce_compare_op(Compare.EQ)
    assert x is Compare.EQ


@pytest.mark.parametrize(
    "text, expected",
    [
        ("==", Compare.EQ),
        ("!=", Compare.NE),
        ("<", Compare.LT),
        ("<=", Compare.LE),
        (">", Compare.GT),
        (">=", Compare.GE),
    ],
)
def test_compare_symbol_mapping_basic(text, expected):
    assert coerce_compare_op(text) is expected


def test_compare_name_case_insensitive():
    assert coerce_compare_op("eq") is Compare.EQ
    assert coerce_compare_op("Ge") is Compare.GE


def test_compare_int_code_valid():
    code = Compare.EQ.value
    assert coerce_compare_op(code) is Compare.EQ


def test_compare_int_code_invalid():
    with pytest.raises(SyntaxError) as exc:
        coerce_compare_op(999_999)
    assert "Invalid COMPARE_OP code" in str(exc.value)


def test_compare_unknown_name():
    with pytest.raises(SyntaxError) as exc:
        coerce_compare_op("spaceship")
    s = str(exc.value)
    assert "Unknown COMPARE_OP name/symbol" in s
    assert "SPACESHIP" in s


def test_compare_bad_type():
    with pytest.raises(SyntaxError) as exc:
        coerce_compare_op(3.14)
    assert "COMPARE_OP expects a symbol/name or int" in str(exc.value)


# -----------------------------
# Identity / Membership (3.13 split)
# -----------------------------


def test_compare_membership_and_identity_symbols():
    # membership
    assert coerce_contains_op("in") is ContainsOp.IN
    assert coerce_contains_op("not in") is ContainsOp.NOT_IN
    # identity
    assert coerce_is_op("is") is IsOp.IS
    assert coerce_is_op("is not") is IsOp.IS_NOT
