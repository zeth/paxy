# tests/test_basic_ops.py
from pathlib import Path
import bytecode
from paxy.compiler.parser import Parser

PROGRAM1 = "PNT 'hello'\nLOAD_CONST None\nRETURN_VALUE\n"
PROGRAM2 = "PNT 42\nLOAD_CONST None\nRETURN_VALUE\n"
PROGRAM3 = "PNT None\nLOAD_CONST None\nRETURN_VALUE\n"
PROGRAM4 = "PNT\nLOAD_CONST None\nRETURN_VALUE\n"  # blank print() -> CALL 0


def as_pairs(instrs):
    """Return [(name:str, arg:Any), ...]"""
    return [(str(i.name), i.arg) for i in instrs]


def strip_frame(pairs):
    """Remove leading RESUME 0 so we compare only the body. Keep the explicit return."""
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    return out


def is_unset_like(arg):
    """Treat arg-less placeholders as equivalent (bytecode UNSET, 0, or None)."""
    # identity / isinstance check for _UNSET
    try:
        if isinstance(arg, bytecode.instr._UNSET):
            return True
    except Exception:
        pass
    # many environments show 0 for arg-less ops
    if arg == 0:
        return True
    # some could leak None; consider it arg-less here
    if arg is None:
        return True
    return False


def canon_argless(pairs):
    """Normalize arg-less ops to a marker so comparisons are stable."""
    out = []
    for name, arg in pairs:
        if name in {"PUSH_NULL", "POP_TOP", "RETURN_VALUE"}:
            out.append((name, "<ARGLESS>" if is_unset_like(arg) else arg))
        else:
            out.append((name, arg))
    return out


def test_print_string(tmp_path: Path):
    src = tmp_path / "p1.paxy"
    src.write_text(PROGRAM1)
    got = canon_argless(strip_frame(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", "<ARGLESS>"),
        ("LOAD_CONST", "hello"),
        ("CALL", 1),
        ("POP_TOP", "<ARGLESS>"),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]


def test_print_number(tmp_path: Path):
    src = tmp_path / "p2.paxy"
    src.write_text(PROGRAM2)
    got = canon_argless(strip_frame(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", "<ARGLESS>"),
        ("LOAD_CONST", 42),
        ("CALL", 1),
        ("POP_TOP", "<ARGLESS>"),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]


def test_print_none_literal(tmp_path: Path):
    src = tmp_path / "p3.paxy"
    src.write_text(PROGRAM3)
    got = canon_argless(strip_frame(as_pairs(Parser().parse_file(src))))
    # Explicit None literal is now a real None in LOAD_CONST
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", "<ARGLESS>"),
        ("LOAD_CONST", None),
        ("CALL", 1),
        ("POP_TOP", "<ARGLESS>"),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]


def test_print_no_arg_blank_line(tmp_path: Path):
    src = tmp_path / "p4.paxy"
    src.write_text(PROGRAM4)
    got = canon_argless(strip_frame(as_pairs(Parser().parse_file(src))))
    # No argument -> CALL 0
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", "<ARGLESS>"),
        ("CALL", 0),
        ("POP_TOP", "<ARGLESS>"),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", "<ARGLESS>"),
    ]
