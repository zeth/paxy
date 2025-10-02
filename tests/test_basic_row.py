# tests/test_basic_row.py

from pathlib import Path
from typing import Any, Iterable, List, Tuple, TypeAlias
import pytest
from paxy.compiler.parser import Parser

Pair: TypeAlias = Tuple[str, Any]
PairList: TypeAlias = List[Pair]

from bytecode.instr import _UNSET as _UNSET_CTOR

UNSET = _UNSET_CTOR()


def as_pairs(instrs: Iterable[Any]) -> PairList:
    return [(str(i.name), getattr(i, "arg", None)) for i in instrs]


def test_row_empty(tmp_path: Path) -> None:
    # Fast path: all literals (zero elems)
    src = tmp_path / "row_empty.paxy"
    src.write_text("ROW r\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", ()),
        ("STORE_NAME", "r"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_row_literals(tmp_path: Path) -> None:
    # Fast path: all literals
    src = tmp_path / "row_literals.paxy"
    src.write_text("ROW r 1 'x' True None\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", (1, "x", True, None)),
        ("STORE_NAME", "r"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_row_with_identifiers_falls_back_to_builder(tmp_path: Path) -> None:
    # Fallback path: mixed identifiers/literals → LOAD_*…; BUILD_TUPLE N
    src = tmp_path / "row_mixed.paxy"
    src.write_text("LET a 10\n" "LET b 20\n" "ROW r a 'x' b\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        # LET a 10
        ("LOAD_CONST", 10),
        ("STORE_NAME", "a"),
        # LET b 20
        ("LOAD_CONST", 20),
        ("STORE_NAME", "b"),
        # ROW r a 'x' b  → builder path
        ("LOAD_NAME", "a"),
        ("LOAD_CONST", "x"),
        ("LOAD_NAME", "b"),
        ("BUILD_TUPLE", 3),
        ("STORE_NAME", "r"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


@pytest.mark.parametrize(
    "program, msg_part",
    [
        ("ROW\n", "ROW expects"),
        ("ROW 1 2\n", "ROW expects"),
    ],
)
def test_row_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "row_err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
