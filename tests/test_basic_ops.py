from pathlib import Path
from paxy.parser import Parser

PROGRAM1 = "PRINT 'hello'\\nRETURN_CONST None\\n"
PROGRAM2 = "PRINT 42\\nRETURN_CONST None\\n"
PROGRAM3 = "PRINT None\\nRETURN_CONST None\\n"
PROGRAM4 = "PRINT\\nRETURN_CONST None\\n"  # blank line

def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]

def test_print_string(tmp_path: Path):
    src = tmp_path / "p1.paxy"
    src.write_text(PROGRAM1)
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", 0),
        ("LOAD_CONST", "hello"),
        ("CALL", 1),
        ("POP_TOP", 0),
        ("RETURN_CONST", None),
    ]

def test_print_number(tmp_path: Path):
    src = tmp_path / "p2.paxy"
    src.write_text(PROGRAM2)
    got = as_pairs(Parser().parse_file(src))
    assert got[0:5] == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", 0),
        ("LOAD_CONST", 42),
        ("CALL", 1),
        ("POP_TOP", 0),
    ]

def test_print_none_literal(tmp_path: Path):
    src = tmp_path / "p3.paxy"
    src.write_text(PROGRAM3)
    got = as_pairs(Parser().parse_file(src))
    assert got[0:5] == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", 0),
        ("LOAD_CONST", None),
        ("CALL", 1),
        ("POP_TOP", 0),
    ]

def test_print_no_arg_blank_line(tmp_path: Path):
    src = tmp_path / "p4.paxy"
    src.write_text(PROGRAM4)
    got = as_pairs(Parser().parse_file(src))
    # CALL 0 (no args)
    assert got[0:5] == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", 0),
        ("CALL", 0),
        ("POP_TOP", 0),
        ("RETURN_CONST", None),
    ][:5]  # tolerate RETURN_CONST positioning in your test slice
