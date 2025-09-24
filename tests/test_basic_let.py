# tests/test_basic_let.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Tuple
import pytest
from paxy.parser import Parser


def as_pairs(instrs: Iterable[Any]) -> List[Tuple[str, Any]]:
    out: List[Tuple[str, Any]] = []
    for i in instrs:
        # These tests only feed sequences of Instr objects.
        # If something else sneaks in, this will raise loudly (which is fine here).
        out.append((str(i.name), getattr(i, "arg", None)))
    return out


def norm_argless(pairs: Iterable[Tuple[str, Any]]) -> List[Tuple[str, Any]]:
    # Normalize arg-less ops like PUSH_NULL/POP_TOP to arg=0 if they show None/enum-zero
    def zeroish(x: Any) -> Any:
        if x is None:
            return 0
        v = getattr(x, "value", x)
        try:
            return 0 if int(v) == 0 else v
        except (TypeError, ValueError):
            return v

    out: List[Tuple[str, Any]] = []
    for n, a in pairs:
        if n in {"PUSH_NULL", "POP_TOP"}:
            out.append((n, zeroish(a)))
        else:
            out.append((n, a))
    return out


def test_let_int(tmp_path: Path) -> None:
    src = tmp_path / "p.paxy"
    src.write_text("LET x 1\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 1),
        ("STORE_NAME", "x"),
        ("RETURN_CONST", 0),
    ]


def test_let_string(tmp_path: Path) -> None:
    src = tmp_path / "p2.paxy"
    src.write_text("LET title 'hi'\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", "hi"),
        ("STORE_NAME", "title"),
        ("RETURN_CONST", 0),
    ]


def test_let_negative_hex_bool_none(tmp_path: Path) -> None:
    p = Parser()
    src = tmp_path / "p3.paxy"
    src.write_text("LET n -42\nLET mask 0xFF\nLET t True\nLET z None\n")
    got = as_pairs(p.parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", -42),
        ("STORE_NAME", "n"),
        ("LOAD_CONST", 255),
        ("STORE_NAME", "mask"),
        ("LOAD_CONST", True),
        ("STORE_NAME", "t"),
        ("LOAD_CONST", None),
        ("STORE_NAME", "z"),
        ("RETURN_CONST", 0),
    ]


def test_let_with_print_in_same_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "p4.paxy"
    src.write_text("LET x 1\nPRINT 'hello'\n")
    instrs = Parser().parse_file(src)

    # Execute quickly using bytecode → code object
    from bytecode import Bytecode, CompilerFlags  # type: ignore[import-not-found]

    bc = Bytecode(instrs)
    bc.filename = str(src)
    bc.name = "<module>"
    # first instruction lineno (Parser ensures a RESUME first)
    bc.first_lineno = instrs[0].lineno or 1  # type: ignore[attr-defined]
    bc.flags |= CompilerFlags.NOFREE
    code = bc.to_code()

    g = {"__name__": "__main__"}
    exec(code, g)
    out = capsys.readouterr().out
    assert out == "hello\n"


@pytest.mark.parametrize(
    ("program", "msg_part"),
    [
        ("LET\n", "LET expects at least"),  # no dst/value
        ("LET x\n", "LET expects at least"),  # missing value
        ("LET 'x' 1\n", "identifier"),  # dst must be identifier
        ("LET 1 2\n", "identifier"),  # dst must be identifier
        ("LET x 1 2\n", "operator form"),  # bad arity for operator form
    ],
)
def test_let_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
