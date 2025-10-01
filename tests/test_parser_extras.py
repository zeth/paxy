# tests/test_parser_extras.py
from pathlib import Path
import pytest
import bytecode

from paxy.compiler.parser import Parser


def as_pairs(instrs):
    """[(name:str, arg:any)] with name coerced to plain str."""
    return [(str(i.name), i.arg) for i in instrs]


def is_unset_like(arg):
    """True for arg-less placeholders: 0, None, or bytecode's UNSET instance."""
    if arg is None:
        return True
    try:
        return (
            isinstance(arg, bytecode.instr._UNSET)
            or int(getattr(arg, "value", arg)) == 0
        )
    except Exception:
        return False


def normalize_argless(pairs):
    """
    Map arg-less ops (PUSH_NULL, POP_TOP, RETURN_VALUE, etc.)
    to a canonical '<ARGLESS>' marker.
    """
    out = []
    for name, arg in pairs:
        if name in {"PUSH_NULL", "POP_TOP", "RETURN_VALUE"}:
            out.append((name, "<ARGLESS>" if is_unset_like(arg) else arg))
        else:
            out.append((name, arg))
    return out


def strip_frame(pairs):
    """Remove only the leading RESUME 0; keep any explicit/auto RETURN_*."""
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    return out


def parse_pairs(src_text: str, tmp_path: Path):
    src = tmp_path / "prog.paxy"
    src.write_text(src_text)
    got = as_pairs(Parser().parse_file(src))
    got = strip_frame(got)
    got = normalize_argless(got)
    return got


def test_negative_integer_argument(tmp_path: Path):
    got = parse_pairs(
        "LOAD_CONST -5\n" "LOAD_CONST None\n" "RETURN_VALUE\n",
        tmp_path,
    )
    assert got == [
        ("LOAD_CONST", -5),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]


def test_hex_and_binary_integer_arguments(tmp_path: Path):
    got = parse_pairs(
        "LOAD_CONST 0xFF\n"  # 255
        "LOAD_CONST 0b1010\n"  # 10
        "LOAD_CONST 0o77\n"  # 63
        "LOAD_CONST None\n"
        "RETURN_VALUE\n",
        tmp_path,
    )
    assert got == [
        ("LOAD_CONST", 255),
        ("LOAD_CONST", 10),
        ("LOAD_CONST", 63),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]


def test_bools_and_none(tmp_path: Path):
    got = parse_pairs(
        "LOAD_CONST True\n" "LOAD_CONST False\n" "LOAD_CONST None\n" "RETURN_VALUE\n",
        tmp_path,
    )
    assert got == [
        ("LOAD_CONST", True),
        ("LOAD_CONST", False),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]


def test_opcode_case_insensitive_and_comment_ignored(tmp_path: Path):
    got = parse_pairs(
        "# a comment line that should be ignored\n"
        "load_name 'print'\n"
        "pUsH_nUlL\n"
        "LOAD_CONST 'hi'\n"
        "CALL 1\n"
        "POP_TOP\n"
        "LOAD_CONST None\n"
        "RETURN_VALUE\n",
        tmp_path,
    )
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", "<ARGLESS>"),
        ("LOAD_CONST", "hi"),
        ("CALL", 1),
        ("POP_TOP", "<ARGLESS>"),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]


def test_trailing_newline_optional(tmp_path: Path):
    got = parse_pairs("LOAD_CONST 1\nLOAD_CONST None\nRETURN_VALUE", tmp_path)
    assert got == [
        ("LOAD_CONST", 1),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]
