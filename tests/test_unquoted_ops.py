# tests/test_unquoted_ops.py
from pathlib import Path
import types
import pytest

from paxy.cli import assemble_file


def _run(src_text: str) -> tuple[dict, str]:
    """Assemble a temp program and run it in an isolated globals dict, returning (globals, stdout)."""
    # We'll capture output by temporarily routing print to a collector
    out = []

    # Tiny shim to collect print output line-by-line (keeps behavior close to builtin print)
    def _print(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        out.append(sep.join(str(a) for a in args) + end)

    g: dict[str, object] = {"print": _print}  # override print in module globals
    code = assemble_file(Path(_write_tmp(src_text)))
    types.FunctionType(code, g)()  # execute module code
    return g, "".join(out)


# --- utility to write temp files via pytest's tmp_path fixture -----------------


def _write_tmp(text: str) -> str:
    import tempfile, os

    fd, path = tempfile.mkstemp(suffix=".paxy")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# -------------------- TESTS --------------------


def test_let_with_unquoted_addition(tmp_path: Path):
    src = (
        "LET a 2\n"
        "LET b 3\n"
        "LET c a + b\n"  # unquoted +
        "PNT c\n"
    )
    g, out = _run(src)
    assert g.get("c") == 5
    assert out.strip().splitlines()[-1] == "5"


def test_unary_minus_literal_in_let(tmp_path: Path):
    src = (
        "LET x -5\n"  # unary minus literal
        "PNT x\n"
    )
    g, out = _run(src)
    assert g.get("x") == -5
    assert out.strip().splitlines()[-1] == "-5"


def test_if_with_unquoted_equality_and_return(tmp_path: Path):
    # SUB zero_or_one(n): if n == 0 -> return 0 else return 1
    src = (
        "SUB zero_or_one n\n"
        "  IF n == 0 ret\n"  # unquoted ==
        "  RET 1\n"
        "  LBL ret\n"
        "  RET 0\n"
        "SBE\n"
        "GOS r1 zero_or_one 0\n"
        "GOS r2 zero_or_one 7\n"
        "PNT r1\n"
        "PNT r2\n"
    )
    g, out = _run(src)
    lines = out.strip().splitlines()
    assert g.get("r1") == 0
    assert g.get("r2") == 1
    assert lines[-2:] == ["0", "1"]


def test_range_body_with_unquoted_addition(tmp_path: Path):
    # Sum 1..4 using RNG and unquoted "+"
    src = (
        "LET total 0\n"
        "RNG i 1 5\n"  # 1,2,3,4
        "  LET total total + i\n"  # unquoted +
        "RNE\n"
        "PNT total\n"
    )
    g, out = _run(src)
    assert g.get("total") == 10
    assert out.strip().splitlines()[-1] == "10"


@pytest.mark.parametrize(
    "a,op,b,expect",
    [
        (3, "<", 5, True),
        (3, "<=", 3, True),
        (4, ">", 9, False),
        (7, ">=", 7, True),
        (5, "==", 5, True),
        (5, "!=", 6, True),
    ],
)
def test_if_with_various_unquoted_comparisons(
    tmp_path: Path, a: int, op: str, b: int, expect: bool
):
    # Build a tiny program dynamically that sets a/b, runs IF a <op> b ret, then prints flag
    src = (
        f"LET a {a}\n"
        f"LET b {b}\n"
        f"LET flag 0\n"
        f"IF a {op} b ret\n"  # unquoted operator under test
        f"LET flag 1\n"
        f"LBL ret\n"
        f"PNT flag\n"
    )
    g, out = _run(src)
    want = (
        0 if expect else 1
    )  # If condition true -> jump to ret (flag stays 0), else flag becomes 1
    assert g.get("flag") == want
    assert out.strip().splitlines()[-1] == str(want)
