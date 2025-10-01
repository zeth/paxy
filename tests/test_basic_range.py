# tests/test_basic_range.py

from pathlib import Path
import types

from bytecode import Instr, Label
import pytest

from paxy.compiler.parser import Parser
from paxy.compiler.ir import RangeBlock
from paxy.compiler.assembler import Assembler
from paxy.cli import assemble_file


def _instr_names(resolved):
    return [i.name for i in resolved if isinstance(i, Instr)]


def test_parser_captures_rangeblock_structure(tmp_path: Path):
    src = tmp_path / "range1.paxy"
    src.write_text("LET total 0\n" "RNG i 1 5\n" '  LET total total "+" i\n' "RNE\n")

    parsed = Parser().parse_file(src)

    rb = next(x for x in parsed if isinstance(x, RangeBlock))
    assert rb.var == "i"
    assert rb.start == 1
    assert rb.end == 5
    assert any(isinstance(x, Instr) for x in rb.body)


def test_assembler_lowers_range_to_for_iter_skeleton(tmp_path: Path):
    src = tmp_path / "range2.paxy"
    src.write_text(
        "LET s 0\n"
        "RNG k 1 4\n"  # Python range(1,4): 1,2,3
        '  LET s s "+" k\n'
        "RNE\n"
    )

    parsed = Parser().parse_file(src)
    resolved = Assembler(parsed).resolve()

    names = _instr_names(resolved)
    # Basic loop skeleton pieces appear
    assert "LOAD_GLOBAL" in names  # range
    assert "CALL" in names
    assert "GET_ITER" in names
    assert "FOR_ITER" in names
    assert "STORE_NAME" in names
    assert "JUMP_BACKWARD" in names
    assert "END_FOR" in names
    assert "POP_TOP" in names


# tests/test_basic_range.py  (only replace the last test)


def test_end_to_end_range_inside_sub(tmp_path: Path):
    """End-to-end: RNG in a SUB (no nested top-level loops)."""
    src = tmp_path / "range3.paxy"
    src.write_text(
        # sum_to(n): sum of 1..(n-1)
        "SUB sum_to n\n"
        "  LET acc 0\n"
        "  RNG i 1 n\n"
        "    LOAD_NAME acc\n"
        "    LOAD_NAME i\n"
        '    BINARY_OP "+" \n'
        "    STORE_NAME acc\n"
        "  RNE\n"
        "  RET acc\n"
        "SBE\n"
        # call sum_to and stash result
        "LET n 5\n"
        "GOS total sum_to n\n"
    )

    code = assemble_file(src)
    g: dict[str, object] = {}
    types.FunctionType(code, g)()  # execute module

    # sum_to(5) with range(1,5): 1+2+3+4 = 10
    assert g.get("total") == 10
