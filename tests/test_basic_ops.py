# tests/test_basic_ops.py
from pathlib import Path

import bytecode
from paxy.parser import Parser, ExplicitNone

PROGRAM1 = "PRINT 'hello'\nRETURN_CONST None\n"
PROGRAM2 = "PRINT 42\nRETURN_CONST None\n"
PROGRAM3 = "PRINT None\nRETURN_CONST None\n"
PROGRAM4 = "PRINT\nRETURN_CONST None\n"  # blank print() -> CALL 0

UNSET = bytecode.instr._UNSET()




def as_pairs(instrs):
    """Return [(name:str, arg:Any), ...]"""
    return [(str(i.name), i.arg) for i in instrs]

def strip_frame(pairs):
    """
    Remove leading RESUME 0 and trailing RETURN_CONST None if present,
    so tests focus on the BASIC op lowering.
    """
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    if out and out[-1] == ("RETURN_CONST", None):
        out.pop()
    return out

def test_print_string(tmp_path: Path):
    src = tmp_path / "p1.paxy"
    src.write_text(PROGRAM1)
    got = strip_frame(as_pairs(Parser().parse_file(src)))
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", UNSET),        # bytecode may expose arg-less as 0
        ("LOAD_CONST", "hello"),
        ("CALL", 1),
        ("POP_TOP", UNSET),
    ]

def test_print_number(tmp_path: Path):
    src = tmp_path / "p2.paxy"
    src.write_text(PROGRAM2)
    got = strip_frame(as_pairs(Parser().parse_file(src)))
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", UNSET),
        ("LOAD_CONST", 42),
        ("CALL", 1),
        ("POP_TOP", UNSET),
    ]

def test_print_none_literal(tmp_path: Path):
    src = tmp_path / "p3.paxy"
    src.write_text(PROGRAM3)
    got = strip_frame(as_pairs(Parser().parse_file(src)))
    enone = got[2][1]
    assert isinstance(enone, ExplicitNone)

    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", UNSET),
        ("LOAD_CONST", enone),
        ("CALL", 1),
        ("POP_TOP", UNSET),
    ]

def test_print_no_arg_blank_line(tmp_path: Path):
    src = tmp_path / "p4.paxy"
    src.write_text(PROGRAM4)
    got = strip_frame(as_pairs(Parser().parse_file(src)))
    # no argument -> CALL 0
    assert got == [
        ("LOAD_NAME", "print"),
        ("PUSH_NULL", UNSET),
        ("CALL", 0),
        ("POP_TOP", UNSET),
    ]
