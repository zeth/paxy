from pathlib import Path

from paxy.compiler.parser import Parser
from tests.helpers import as_pairs
from bytecode.instr import _UNSET

UNSET = _UNSET()


def test_MAD_simple(tmp_path: Path) -> None:
    # Start with one entry via MAP, then add one via MAD.
    src = tmp_path / "m_add1.paxy"
    src.write_text("MAP m 'a' 1\nMAD m 'b' 2\n")

    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        # MAP m 'a' 1 -> build via MAP_ADD, then bind to m
        ("BUILD_MAP", 0),
        ("LOAD_CONST", "a"),
        ("LOAD_CONST", 1),
        ("MAP_ADD", 1),
        ("STORE_NAME", "m"),
        # MAD m 'b' 2 -> mutate existing dict: m['b'] = 2
        ("LOAD_NAME", "m"),
        ("LOAD_CONST", "b"),
        ("LOAD_CONST", 2),
        ("STORE_SUBSCR", UNSET),  # no-arg op; normalized as 0
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_MAD_with_variable_value(tmp_path: Path) -> None:
    # The value to insert comes from a variable.
    src = tmp_path / "m_add2.paxy"
    src.write_text("LET v 42\nMAP m\nMAD m 'answer' v\n")

    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        ("LOAD_CONST", 42),
        ("STORE_NAME", "v"),
        # MAP m -> empty dict, then bind
        ("BUILD_MAP", 0),
        ("STORE_NAME", "m"),
        # MAD m 'answer' v  -> m['answer'] = v
        ("LOAD_NAME", "m"),
        ("LOAD_CONST", "answer"),
        ("LOAD_NAME", "v"),
        ("STORE_SUBSCR", UNSET),  # no-arg op; normalized as 0
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]
