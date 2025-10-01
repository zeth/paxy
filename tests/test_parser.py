# tests/test_parser.py
from pathlib import Path
import bytecode
import pytest

# Adjust this import to wherever your Parser class lives:
# - if it's in paxy/parser.py -> from paxy.compiler.parser import Parser
# - if it's in paxy/__init__.py -> from paxy import Parser
from paxy.compiler.parser import Parser  # <- change if needed


PROGRAM = """\
RESUME 0
LOAD_NAME 'print'
PUSH_NULL
LOAD_CONST 'hello'
CALL 1
POP_TOP
LOAD_CONST None;
RETURN_VALUE
"""


def names_and_args(instrs):
    names = [str(ins.name) for ins in instrs]
    args = [ins.arg for ins in instrs]
    return names, args


def is_unset(item):
    return isinstance(item, bytecode.instr._UNSET)


def assert_prog(instrs):
    names = [str(ins.name) for ins in instrs]
    args = [ins.arg for ins in instrs]

    # 1) Names in exact order
    assert names == [
        "RESUME",
        "LOAD_NAME",
        "PUSH_NULL",
        "LOAD_CONST",
        "CALL",
        "POP_TOP",
        "LOAD_CONST",
        "RETURN_VALUE",
    ]

    # 2) Args with robust check
    assert args[0] == 0  # RESUME 0
    assert args[1] == "print"  # LOAD_NAME 'print'
    assert is_unset(args[2])
    assert args[3] == "hello"  # LOAD_CONST 'hello'
    assert int(getattr(args[4], "value", args[4])) == 1  # CALL 1 (tolerate enum/int)
    assert is_unset(args[5])  # POP_TOP
    assert args[6] is None  # LOAD_CONST None


def test_parser_emits_expected_instrs(tmp_path: Path):
    src = tmp_path / "hello.paxy"
    src.write_text(PROGRAM)

    p = Parser()
    instrs = p.parse_file(src)

    assert_prog(instrs)


def test_parser_handles_no_trailing_newline(tmp_path: Path):
    # Same program without the final newline; should still parse
    src = tmp_path / "hello2.paxy"
    src.write_text(PROGRAM.rstrip("\n"))

    p = Parser()
    instrs = p.parse_file(src)

    assert_prog(instrs)
