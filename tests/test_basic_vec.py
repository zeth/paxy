# tests/test_basic_vec.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable, List, Tuple, TypeAlias
import pytest
from paxy.parser import Parser

Pair: TypeAlias = Tuple[str, Any]
PairList: TypeAlias = List[Pair]


def as_pairs(instrs: Iterable[Any]) -> PairList:
    return [(str(i.name), getattr(i, "arg", None)) for i in instrs]


def test_vec_empty(tmp_path: Path) -> None:
    src = tmp_path / "v1.paxy"
    src.write_text("VEC xs\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("BUILD_LIST", 0),
        ("STORE_NAME", "xs"),
        ("RETURN_CONST", 0),
    ]


def test_vec_constants(tmp_path: Path) -> None:
    src = tmp_path / "v2.paxy"
    src.write_text("VEC xs 1 'a' True None\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 1),
        ("LOAD_CONST", "a"),
        ("LOAD_CONST", True),
        ("LOAD_CONST", None),
        ("BUILD_LIST", 4),
        ("STORE_NAME", "xs"),
        ("RETURN_CONST", 0),
    ]


def test_vec_with_identifiers(tmp_path: Path) -> None:
    src = tmp_path / "v3.paxy"
    src.write_text("LET a 10\n" "LET b 20\n" "VEC xs a 'x' b\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 10),
        ("STORE_NAME", "a"),
        ("LOAD_CONST", 20),
        ("STORE_NAME", "b"),
        ("LOAD_NAME", "a"),
        ("LOAD_CONST", "x"),
        ("LOAD_NAME", "b"),
        ("BUILD_LIST", 3),
        ("STORE_NAME", "xs"),
        ("RETURN_CONST", 0),
    ]
