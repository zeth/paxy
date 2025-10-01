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


def test_MAD_simple(tmp_path: Path) -> None:
    src = tmp_path / "ma1.paxy"
    src.write_text("MAP m 'a' 1\n" "MAD m 'b' 2\n")
    got = as_pairs(Parser().parse_file(src))

    # Assert just the opcode names in order
    names = [n for (n, _) in got]
    assert names == [
        "RESUME",
        "LOAD_CONST",
        "LOAD_CONST",
        "BUILD_CONST_KEY_MAP",
        "STORE_NAME",
        "LOAD_NAME",
        "LOAD_CONST",
        "LOAD_CONST",
        "STORE_SUBSCR",
        "RETURN_CONST",
    ]

    # Now assert only the args we care about
    assert got[0][0] == "RESUME"
    assert int(got[0][1]) == 0
    assert got[1] == ("LOAD_CONST", ("a",))
    assert got[2] == ("LOAD_CONST", 1)
    assert got[4] == ("STORE_NAME", "m")
    assert got[5] == ("LOAD_NAME", "m")
    assert got[6] == ("LOAD_CONST", "b")
    assert got[7] == ("LOAD_CONST", 2)
    assert got[8] == ("STORE_SUBSCR", UNSET)
    assert got[9] == ("RETURN_CONST", 0)


def test_MAD_with_variable_value(tmp_path: Path) -> None:
    src = tmp_path / "ma2.paxy"
    src.write_text("LET v 42\n" "MAP m 'x' 1\n" "MAD m 'v' v\n")
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
        "LOAD_CONST",
        "LOAD_NAME",
        "STORE_SUBSCR",
        "RETURN_CONST",
    ]

    # LET v 42
    assert got[0][0] == "RESUME"
    assert int(got[0][1]) == 0
    assert got[1] == ("LOAD_CONST", 42)
    assert got[2] == ("STORE_NAME", "v")
    # MAP m 'x' 1
    assert got[3] == ("LOAD_CONST", ("x",))
    assert got[4] == ("LOAD_CONST", 1)
    assert got[6] == ("STORE_NAME", "m")
    # MAD m 'v' v
    assert got[7] == ("LOAD_NAME", "m")
    assert got[8] == ("LOAD_CONST", "v")
    assert got[9] == ("LOAD_NAME", "v")
    assert got[10] == ("STORE_SUBSCR", UNSET)
    assert got[11] == ("RETURN_CONST", 0)


@pytest.mark.parametrize(
    "program, msg_part",
    [
        ("MAD\n", "MAD expects"),
        ("MAD m\n", "MAD expects"),
        ("MAD m 'k'\n", "MAD expects"),
        ("MAD 1 2 3\n", "MAD expects"),
    ],
)
def test_MAD_errors(tmp_path: Path, program: str, msg_part: str) -> None:
    src = tmp_path / "ma_err.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_part in str(exc.value)
