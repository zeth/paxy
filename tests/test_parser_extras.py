# tests/test_parser_extra.py
from pathlib import Path
import bytecode
import pytest

# Adjust if your Parser lives elsewhere
from paxy.parser import Parser


def as_pairs(instrs):
    """Return [(name:str, arg:any), ...] for comparison."""
    return [(str(ins.name), ins.arg) for ins in instrs]


def test_negative_integer_argument(tmp_path: Path):
    src = tmp_path / "neg.paxy"
    src.write_text(
        "LOAD_CONST -5\n"
        "RETURN_CONST None\n"
    )
    p = Parser()
    got = as_pairs(p.parse_file(src))
    assert got == [("LOAD_CONST", -5), ("RETURN_CONST", None)]


def test_hex_and_binary_integer_arguments(tmp_path: Path):
    src = tmp_path / "bases.paxy"
    src.write_text(
        "LOAD_CONST 0xFF\n"   # 255
        "LOAD_CONST 0b1010\n" # 10
        "LOAD_CONST 0o77\n"   # 63
        "RETURN_CONST None\n"
    )
    p = Parser()
    got = as_pairs(p.parse_file(src))
    assert got == [
        ("LOAD_CONST", 255),
        ("LOAD_CONST", 10),
        ("LOAD_CONST", 63),
        ("RETURN_CONST", None),
    ]


def test_bools_and_none(tmp_path: Path):
    src = tmp_path / "bools.paxy"
    src.write_text(
        "LOAD_CONST True\n"
        "LOAD_CONST False\n"
        "RETURN_CONST None\n"
    )
    p = Parser()
    got = as_pairs(p.parse_file(src))
    assert got == [
        ("LOAD_CONST", True),
        ("LOAD_CONST", False),
        ("RETURN_CONST", None),
    ]


def test_opcode_case_insensitive_and_comment_ignored(tmp_path: Path):
    # Lower/mixed-case opcode should be accepted (parser uppercases & validates).
    # Lines starting with '#' should be ignored by tokenize as COMMENT.
    src = tmp_path / "case_comment.paxy"
    src.write_text(
        "# a comment line that should be ignored\n"
        "load_name 'print'\n"
        "pUsH_nUlL\n"
        "LOAD_CONST 'hi'\n"
        "CALL 1\n"
        "POP_TOP\n"
        "RETURN_CONST None\n"
    )
    p = Parser()
    got = as_pairs(p.parse_file(src))
    # Expect exactly the canonical op names with correct args
    unset = bytecode.instr._UNSET()
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", unset),       # arg-less op may appear as 0
        ("LOAD_CONST", "hi"),
        ("CALL", 1),
        ("POP_TOP", unset),         # arg-less op may appear as 0
        ("RETURN_CONST", None),
    ]


def test_extra_token_on_line_raises(tmp_path: Path):
    # Two arguments on one line should raise (parser allows at most one).
    src = tmp_path / "extra_arg.paxy"
    src.write_text("LOAD_CONST 1 2\n")
    p = Parser()
    with pytest.raises(SyntaxError):
        p.parse_file(src)
