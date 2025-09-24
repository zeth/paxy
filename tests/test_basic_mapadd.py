# tests/test_basic_mapadd.py
from __future__ import annotations
from pathlib import Path
from typing import Any, List, Tuple, TypeAlias
import pytest
from paxy.parser import Parser

Pair: TypeAlias = Tuple[str, Any]
PairList: TypeAlias = List[Pair]


def as_pairs(instrs) -> PairList:
    return [(str(i.name), getattr(i, "arg", None)) for i in instrs]


def test_mapadd_simple(tmp_path: Path) -> None:
    src = tmp_path / "ma1.paxy"
    src.write_text("MAP m 'a' 1\n" "MAPADD m 'b' 2\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", ("a",)),  # MAP creation
        ("LOAD_CONST", 1),
        ("BUILD_CONST_KEY_MAP", 1),
        ("STORE_NAME", "m"),
        ("LOAD_NAME", "m"),  # MAPADD
        ("LOAD_CONST", "b"),
        ("LOAD_CONST", 2),
        ("STORE_SUBSCR", None),
        ("RETURN_CONST", 0),
    ]


def test_mapadd_with_variable_value(tmp_path: Path) -> None:
    src = tmp_path / "ma2.paxy"
    src.write_text("LET v 42\n" "MAP m 'x' 1\n" "MAPADD m 'v' v\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 42),
        ("STORE_NAME", "v"),
        ("LOAD_CONST", ("x",)),
        ("LOAD_CONST", 1),
        ("BUILD_CONST_KEY_MAP", 1),
        ("STORE_NAME", "m"),
        ("LOAD_NAME", "m"),
        ("LOAD_CONST", "v"),
        ("LOAD_NAME", "v"),
        ("STORE_SUBSCR", None),
        ("RETURN_CONST", 0),
    ]


@pytest.mark.parametrize(
    "program, msg_part",
    [
        ("MAPADD\n", "MAPADD expects"),
        ("MAPADD m\n", "MAPADD expects"),
        ("MAPADD m 'k'\n", "MAPADD expects"),
        ("MAPADD 1 2 3\n", "MAPADD expects"),
    ],
)
def test_mapadd_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "ma_err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
