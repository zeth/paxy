# tests/test_subroutines.py
from __future__ import annotations

from pathlib import Path
from types import CodeType
import pytest

from paxy.assembler import assemble_file


def test_sub_gosub_side_effect(tmp_path: Path) -> None:
    """
    Define a SUB that sets a global variable, then GOSUB it and
    assert the side-effect is visible in the module globals.
    """
    src = tmp_path / "sub1.paxy"
    src.write_text(
        # Define a subroutine that sets a global flag
        "SUB setflag\n"
        "  LET flag True\n"
        "SUBEND\n"
        # Call it
        "GOSUB setflag\n"
    )

    code: CodeType = assemble_file(src)
    g = {"__name__": "__main__"}
    exec(code, g)

    assert g.get("flag") is True


def test_sub_callfn_returns_value(tmp_path: Path) -> None:
    """
    Define a SUB that returns a value, call it via CALLFN to store the result,
    and assert the stored value is correct.

    Assumes CALLFN syntax: CALLFN <dest> <name> [args...]
    """
    src = tmp_path / "sub2.paxy"
    src.write_text(
        # add(a, b) -> a + b
        "SUB add a b\n"
        "  LET tmp a '+' b\n"  # compute inside the sub
        "  RETURN tmp\n"  # RETURN accepts at most one arg in current impl
        "SUBEND\n"
        # r = add(2, 3)
        "CALLFN r add 2 3\n"
    )

    code: CodeType = assemble_file(src)
    g = {"__name__": "__main__"}
    exec(code, g)

    assert g.get("r") == 5
