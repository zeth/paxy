# tests/test_examples_printers.py
from pathlib import Path
import dis
import bytecode
import pytest

from paxy.compiler.parser import Parser
from paxy.cli import assemble_file

UNSET = bytecode.instr._UNSET()


EXPLICIT = """\
RESUME 0
LOAD_NAME 'print'
PUSH_NULL
LOAD_CONST 'hello'
CALL 1
POP_TOP
LOAD_CONST 0
RETURN_VALUE
"""

BASIC = """\
RESUME 0
PNT 'hello'
LOAD_CONST 0
RETURN_VALUE
"""

MINIMAL = """\
PNT 'hello'
"""


def as_pairs(instrs):
    """
    Return [(name:str, arg:Any), ...].
    Coerce name to str (bytecode may expose enum-like names).
    """
    return [(str(i.name), i.arg) for i in instrs]


def norm_argless(pairs):
    """
    Normalize arg-less opcode args: treat 0/None/_enum(0) as 0
    for stable comparison across environments.
    """

    def zeroish(x):
        if x is None:
            return 0
        v = getattr(x, "value", x)
        try:
            return 0 if int(v) == 0 else v
        except (TypeError, ValueError):
            return v

    out = []
    for name, arg in pairs:
        if name in {"PUSH_NULL", "POP_TOP"}:
            out.append((name, zeroish(arg)))
        else:
            out.append((name, arg))
    return out


def test_basic_and_explicit_parse_to_same_lowered_sequence(tmp_path: Path):
    p1 = tmp_path / "printer.paxy"
    p2 = tmp_path / "printer_basic.paxy"
    p1.write_text(EXPLICIT)
    p2.write_text(BASIC)

    parser = Parser()
    instrs_explicit = parser.parse_file(p1)
    instrs_basic = parser.parse_file(p2)

    got_explicit = norm_argless(as_pairs(instrs_explicit))
    got_basic = norm_argless(as_pairs(instrs_basic))

    assert (
        got_basic
        == got_explicit
        == [
            ("RESUME", 0),
            ("LOAD_NAME", "print"),
            ("PUSH_NULL", UNSET),
            ("LOAD_CONST", "hello"),
            ("CALL", 1),
            ("POP_TOP", UNSET),
            ("LOAD_CONST", 0),
            ("RETURN_VALUE", UNSET),
        ]
    )


def test_minimal_is_auto_framed_and_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    src = tmp_path / "printer_minimal.paxy"
    src.write_text(MINIMAL)

    # Assemble + exec: should print "hello"
    code = assemble_file(src)
    g = {"__name__": "__main__"}
    exec(code, g)
    out = capsys.readouterr().out
    assert out == "hello\n"

    # Disassemble to ensure a RESUME and a RETURN_CONST exist
    # (we don't assert exact positions; just that they were auto-added)
    dis_text = dis.Bytecode(code).dis()
    assert "RESUME" in dis_text
    assert "RETURN_VALUE" in dis_text
