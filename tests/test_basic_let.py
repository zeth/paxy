# tests/test_basic_let.py

from pathlib import Path
from typing import Any, Iterable, List, Tuple, TypeAlias
import bytecode
import pytest
from paxy.compiler.parser import Parser
from tests.helpers import run_paxy_path

UNSET = bytecode.instr._UNSET()


# ---- Type aliases ----
Pair: TypeAlias = Tuple[str, Any]
PairList: TypeAlias = List[Pair]


# ---- Helpers ----
def _denum(x: Any) -> Any:
    """Return enum .name if present; otherwise the value as-is."""
    if x is None:
        return None
    name = getattr(x, "name", None)
    if name is not None:
        return name
    return x


def as_pairs(instrs: Iterable[Any]) -> PairList:
    out: PairList = []
    for i in instrs:
        out.append((str(i.name), getattr(i, "arg", None)))
    return out


def as_pairs_names(instrs: Iterable[Any]) -> PairList:
    """Like as_pairs, but convert enum args to their .name for easy assertions."""
    out: PairList = []
    for i in instrs:
        arg = getattr(i, "arg", None)
        out.append((str(i.name), _denum(arg)))
    return out


def norm_argless(pairs: Iterable[Pair]) -> PairList:
    # Normalize arg-less ops like PUSH_NULL/POP_TOP to arg=0 if they show None/enum-zero
    def zeroish(x: Any) -> Any:
        if x is None:
            return 0
        v = getattr(x, "value", x)
        try:
            return 0 if int(v) == 0 else v
        except (TypeError, ValueError):
            return v

    out: PairList = []
    for n, a in pairs:
        if n in {"PUSH_NULL", "POP_TOP"}:
            out.append((n, zeroish(a)))
        else:
            out.append((n, a))
    return out


# ---- Existing tests (simple LET) ----
def test_let_int(tmp_path: Path) -> None:
    src = tmp_path / "p.paxy"
    src.write_text("LET x 1\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 1),
        ("STORE_NAME", "x"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_let_string(tmp_path: Path) -> None:
    src = tmp_path / "p2.paxy"
    src.write_text("LET title 'hi'\n")
    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", "hi"),
        ("STORE_NAME", "title"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
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
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_let_with_print_in_same_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "p4.paxy"
    src.write_text("LET x 1\nPNT 'hello'\n")
    run_paxy_path(src)
    out = capsys.readouterr().out
    assert out == "hello\n"


@pytest.mark.parametrize(
    ("program", "msg_part"),
    [
        ("LET\n", "LET expects at least"),
        ("LET x\n", "LET expects at least"),
        ("LET 'x' 1\n", "identifier"),
        ("LET 1 2\n", "identifier"),
        ("LET x 1 2\n", "operator form"),
    ],
)
def test_let_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)


# ---- New tests: operator-form LET ----


def test_let_binary_add(tmp_path: Path) -> None:
    src = tmp_path / "op1.paxy"
    src.write_text("LET a 2\n" "LET b 3\n" "LET z a '+' b\n")
    got = as_pairs_names(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 2),
        ("STORE_NAME", "a"),
        ("LOAD_CONST", 3),
        ("STORE_NAME", "b"),
        ("LOAD_NAME", "a"),
        ("LOAD_NAME", "b"),
        ("BINARY_OP", "ADD"),
        ("STORE_NAME", "z"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_let_compare_eq(tmp_path: Path) -> None:
    src = tmp_path / "op2.paxy"
    src.write_text("LET a 5\n" "LET b 5\n" "LET ok a '==' b\n")
    got = as_pairs_names(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 5),
        ("STORE_NAME", "a"),
        ("LOAD_CONST", 5),
        ("STORE_NAME", "b"),
        ("LOAD_NAME", "a"),
        ("LOAD_NAME", "b"),
        ("COMPARE_OP", "EQ"),
        ("STORE_NAME", "ok"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_let_identity_is(tmp_path: Path) -> None:
    src = tmp_path / "op3.paxy"
    src.write_text("LET a None\n" "LET b None\n" "LET same a 'is' b\n")
    got = as_pairs_names(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", None),
        ("STORE_NAME", "a"),
        ("LOAD_CONST", None),
        ("STORE_NAME", "b"),
        ("LOAD_NAME", "a"),
        ("LOAD_NAME", "b"),
        ("IS_OP", "IS"),
        ("STORE_NAME", "same"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_let_membership_in(tmp_path: Path) -> None:
    # NOTE: bracketed list literals like `[1, 2, 3]` are not parsed as a single value by the .paxy tokenizer yet.
    # Using a string container keeps this test within current parser capabilities.
    src = tmp_path / "op4.paxy"
    src.write_text("LET s 'abc'\n" "LET ch 'b'\n" "LET present ch 'in' s\n")
    got = as_pairs_names(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", "abc"),
        ("STORE_NAME", "s"),
        ("LOAD_CONST", "b"),
        ("STORE_NAME", "ch"),
        ("LOAD_NAME", "ch"),
        ("LOAD_NAME", "s"),
        ("CONTAINS_OP", "IN"),
        ("STORE_NAME", "present"),
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]
