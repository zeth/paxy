# tests/test_basic_map
from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable, List, Tuple, TypeAlias
import pytest
from paxy.compiler.parser import Parser

Pair: TypeAlias = Tuple[str, Any]
PairList: TypeAlias = List[Pair]


def as_pairs(instrs: Iterable[Any]) -> PairList:
    return [(str(i.name), getattr(i, "arg", None)) for i in instrs]


def test_map_empty(tmp_path: Path) -> None:
    src = tmp_path / "m0.paxy"
    src.write_text("MAP m\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", ()),  # empty keys tuple
        ("BUILD_CONST_KEY_MAP", 0),
        ("STORE_NAME", "m"),
        ("RETURN_CONST", 0),
    ]


def test_map_constant_keys_and_values(tmp_path: Path) -> None:
    src = tmp_path / "m1.paxy"
    src.write_text("MAP m 'a' 1 'b' 2\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", ("a", "b")),  # keys tuple
        ("LOAD_CONST", 1),
        ("LOAD_CONST", 2),
        ("BUILD_CONST_KEY_MAP", 2),
        ("STORE_NAME", "m"),
        ("RETURN_CONST", 0),
    ]


def test_map_constant_keys_identifier_values(tmp_path: Path) -> None:
    src = tmp_path / "m2.paxy"
    src.write_text("LET v 42\n" "MAP m 'answer' v 'pi' 3.14\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 42),
        ("STORE_NAME", "v"),
        ("LOAD_CONST", ("answer", "pi")),
        ("LOAD_NAME", "v"),
        ("LOAD_CONST", 3.14),
        ("BUILD_CONST_KEY_MAP", 2),
        ("STORE_NAME", "m"),
        ("RETURN_CONST", 0),
    ]


@pytest.mark.parametrize(
    "program, msg_part",
    [
        ("MAP\n", "MAP expects"),
        ("MAP 1 2\n", "MAP expects"),
        ("MAP m 'a' 1 'b'\n", "even number"),
        ("MAP m k 1\n", "literal strings"),
        ("MAP m 1 2\n", "keys must be strings"),
    ],
)
def test_map_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "m_err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
