from pathlib import Path
import bytecode
import pytest
from typing import Any, Iterable, Tuple, List
from paxy.compiler.parser import Parser

Pair = Tuple[str, Any]
PairList = List[Pair]

UNSET = bytecode.instr._UNSET()


def as_pairs(instrs: Iterable[Any]) -> PairList:
    return [(str(i.name), getattr(i, "arg", None)) for i in instrs]


def test_mapdel_simple(tmp_path: Path) -> None:
    src = tmp_path / "md1.paxy"
    src.write_text("MAP m 'a' 1 'b' 2\n" "MAPDEL m 'a'\n")
    got = as_pairs(Parser().parse_file(src))

    names = [n for (n, _) in got]
    assert names == [
        "RESUME",
        "LOAD_CONST",
        "LOAD_CONST",
        "LOAD_CONST",
        "BUILD_CONST_KEY_MAP",
        "STORE_NAME",
        "LOAD_NAME",
        "LOAD_CONST",
        "DELETE_SUBSCR",
        "RETURN_CONST",
    ]

    assert got[0][0] == "RESUME"
    assert int(got[0][1]) == 0
    assert got[1] == ("LOAD_CONST", ("a", "b"))
    assert got[2] == ("LOAD_CONST", 1)
    assert got[3] == ("LOAD_CONST", 2)
    assert got[5] == ("STORE_NAME", "m")
    assert got[6] == ("LOAD_NAME", "m")
    assert got[7] == ("LOAD_CONST", "a")
    assert got[8] == ("DELETE_SUBSCR", UNSET)
    assert got[9] == ("RETURN_CONST", 0)


def test_mapdel_with_identifier_key(tmp_path: Path) -> None:
    src = tmp_path / "md2.paxy"
    src.write_text("LET k 'x'\n" "MAP m 'x' 1\n" "MAPDEL m k\n")
    got = as_pairs(Parser().parse_file(src))

    names = [n for (n, _) in got]
    assert names == [
        "RESUME",
        "LOAD_CONST",
        "STORE_NAME",
        "LOAD_CONST",
        "LOAD_CONST",
        "BUILD_CONST_KEY_MAP",
        "STORE_NAME",
        "LOAD_NAME",
        "LOAD_NAME",
        "DELETE_SUBSCR",
        "RETURN_CONST",
    ]

    # LET k 'x'
    assert got[0][0] == "RESUME"
    assert int(got[0][1]) == 0
    assert got[1] == ("LOAD_CONST", "x")
    assert got[2] == ("STORE_NAME", "k")
    # MAP m 'x' 1
    assert got[3] == ("LOAD_CONST", ("x",))
    assert got[4] == ("LOAD_CONST", 1)
    assert got[6] == ("STORE_NAME", "m")
    # MAPDEL m k
    assert got[7] == ("LOAD_NAME", "m")
    assert got[8] == ("LOAD_NAME", "k")
    assert got[9] == ("DELETE_SUBSCR", UNSET)
    assert got[10] == ("RETURN_CONST", 0)


@pytest.mark.parametrize(
    "program, msg_part",
    [
        ("MAPDEL\n", "MAPDEL expects"),
        ("MAPDEL m\n", "MAPDEL expects"),
        ("MAPDEL 1 'a'\n", "MAPDEL expects"),
    ],
)
def test_mapdel_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "md_err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
