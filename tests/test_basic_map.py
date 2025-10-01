# tests/test_basic_map.py
from pathlib import Path
from typing import Any, Iterable, List, Tuple, TypeAlias
import pytest
from paxy.compiler.parser import Parser

# 3.14: RETURN_VALUE carries an UNSET arg
from bytecode.instr import _UNSET as _UNSET_CTOR  # sentinel constructor

UNSET = _UNSET_CTOR()

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
        ("BUILD_MAP", 0),
        ("STORE_NAME", "m"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_map_constant_keys_and_values(tmp_path: Path) -> None:
    src = tmp_path / "m1.paxy"
    src.write_text("MAP m 'a' 1 'b' 2\n")
    got = as_pairs(Parser().parse_file(src))
    # Fallback form: BUILD_MAP; for each pair: LOAD_CONST key, LOAD_* value, MAP_ADD 1
    assert got == [
        ("RESUME", 0),
        ("BUILD_MAP", 0),
        ("LOAD_CONST", "a"),
        ("LOAD_CONST", 1),
        ("MAP_ADD", 1),
        ("LOAD_CONST", "b"),
        ("LOAD_CONST", 2),
        ("MAP_ADD", 1),
        ("STORE_NAME", "m"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_map_constant_keys_identifier_values(tmp_path: Path) -> None:
    src = tmp_path / "m2.paxy"
    src.write_text("LET v 42\nMAP m 'answer' v 'pi' 3.14\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 42),
        ("STORE_NAME", "v"),
        ("BUILD_MAP", 0),
        ("LOAD_CONST", "answer"),
        ("LOAD_NAME", "v"),
        ("MAP_ADD", 1),
        ("LOAD_CONST", "pi"),
        ("LOAD_CONST", 3.14),
        ("MAP_ADD", 1),
        ("STORE_NAME", "m"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_map_identifier_key_allowed(tmp_path: Path) -> None:
    # key is an identifier (runtime string)
    src = tmp_path / "m3.paxy"
    src.write_text("LET k 'user'\nMAP m k 7 'age' 30\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", "user"),
        ("STORE_NAME", "k"),
        ("BUILD_MAP", 0),
        ("LOAD_NAME", "k"),
        ("LOAD_CONST", 7),
        ("MAP_ADD", 1),
        ("LOAD_CONST", "age"),
        ("LOAD_CONST", 30),
        ("MAP_ADD", 1),
        ("STORE_NAME", "m"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


@pytest.mark.parametrize(
    "program, msg_part",
    [
        ("MAP\n", "MAP expects"),
        ("MAP 1 2\n", "MAP expects"),
        ("MAP m 'a' 1 'b'\n", "even number of key/value arguments"),
    ],
)
def test_map_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "m_err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
