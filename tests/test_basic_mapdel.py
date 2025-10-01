from pathlib import Path

from paxy.compiler.parser import Parser
from tests.helpers import as_pairs
from bytecode.instr import _UNSET

UNSET = _UNSET()


def test_mapdel_simple(tmp_path: Path) -> None:
    # Create a map with two entries, then delete one with MAL.
    src = tmp_path / "m_del1.paxy"
    src.write_text("MAP m 'a' 1 'b' 2\nMAL m 'a'\n")

    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        # MAP m 'a' 1 'b' 2 -> build via MAP_ADD, then bind to m
        ("BUILD_MAP", 0),
        ("LOAD_CONST", "a"),
        ("LOAD_CONST", 1),
        ("MAP_ADD", 1),
        ("LOAD_CONST", "b"),
        ("LOAD_CONST", 2),
        ("MAP_ADD", 1),
        ("STORE_NAME", "m"),
        # MAL m 'a' -> del m['a']
        ("LOAD_NAME", "m"),
        ("LOAD_CONST", "a"),
        ("DELETE_SUBSCR", UNSET),  # no-arg op; normalized as 0
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]


def test_mapdel_with_identifier_key(tmp_path: Path) -> None:
    # Deleting with a key coming from a variable (still a string at runtime).
    src = tmp_path / "m_del2.paxy"
    src.write_text("LET k 'alpha'\nLET v 99\nMAP m k v\nMAL m k\n")

    got = as_pairs(Parser().parse_file(src))
    assert got == [
        ("RESUME", 0),
        # LET k 'alpha'
        ("LOAD_CONST", "alpha"),
        ("STORE_NAME", "k"),
        # LET v 99
        ("LOAD_CONST", 99),
        ("STORE_NAME", "v"),
        # MAP m k v -> build via MAP_ADD, then bind to m
        ("BUILD_MAP", 0),
        ("LOAD_NAME", "k"),
        ("LOAD_NAME", "v"),
        ("MAP_ADD", 1),
        ("STORE_NAME", "m"),
        # MAL m k  -> del m[k]
        ("LOAD_NAME", "m"),
        ("LOAD_NAME", "k"),
        ("DELETE_SUBSCR", UNSET),  # no-arg op; normalized as 0
        ("LOAD_CONST", 0),
        ("RETURN_VALUE", UNSET),
    ]
