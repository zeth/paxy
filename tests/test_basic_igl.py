# tests/test_basic_igl.py

from pathlib import Path
from typing import Any, Iterable, List, Tuple, TypeAlias
import pytest
from paxy.compiler.parser import Parser

# 3.14: RETURN_VALUE carries bytecode.instr._UNSET() when there's no explicit value
from bytecode.instr import _UNSET as _UNSET_CTOR

UNSET = _UNSET_CTOR()

Pair: TypeAlias = Tuple[str, Any]
PairList: TypeAlias = List[Pair]


def as_pairs(instrs: Iterable[Any]) -> PairList:
    return [(str(i.name), getattr(i, "arg", None)) for i in instrs]


def test_igl_empty(tmp_path: Path) -> None:
    # Fast path: all literals (zero elems) → frozenset()
    src = tmp_path / "igl_empty.paxy"
    src.write_text("IGL s\n")
    got = as_pairs(Parser().parse_file(src))
    assert got[0] == ("RESUME", 0)
    assert got[-1] == ("RETURN_VALUE", UNSET)
    op, val = got[1]
    assert op == "LOAD_CONST" and isinstance(val, frozenset) and len(val) == 0
    assert got[2] == ("STORE_NAME", "s")


def test_igl_literals_fast_path(tmp_path: Path) -> None:
    # Fast path: all literals (hashable) → single LOAD_CONST frozenset
    src = tmp_path / "igl_literals.paxy"
    src.write_text("IGL s 1 'x' True None\n")
    got = as_pairs(Parser().parse_file(src))
    assert got[0] == ("RESUME", 0)
    assert got[-1] == ("RETURN_VALUE", UNSET)
    op, val = got[1]
    assert op == "LOAD_CONST" and isinstance(val, frozenset)
    assert {1, "x", True, None}.issubset(val)
    assert got[2] == ("STORE_NAME", "s")


def test_igl_with_identifiers_falls_back_to_call(tmp_path: Path) -> None:
    # Fallback path: identifiers present → LOAD_NAME 'frozenset'; LOAD_*…; BUILD_TUPLE; CALL 1
    src = tmp_path / "igl_mixed.paxy"
    src.write_text("LET a 10\n" "LET b 20\n" "IGL s a 'x' b\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        # LET a 10
        ("LOAD_CONST", 10),
        ("STORE_NAME", "a"),
        # LET b 20
        ("LOAD_CONST", 20),
        ("STORE_NAME", "b"),
        # IGL s a 'x' b  → fallback via function call
        ("LOAD_NAME", "frozenset"),
        ("LOAD_NAME", "a"),
        ("LOAD_CONST", "x"),
        ("LOAD_NAME", "b"),
        ("BUILD_TUPLE", 3),
        ("CALL", 1),
        ("STORE_NAME", "s"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


@pytest.mark.parametrize(
    "program, msg_part",
    [
        ("IGL\n", "IGL expects"),
        ("IGL 1 2\n", "IGL expects"),
    ],
)
def test_igl_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "igl_err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
