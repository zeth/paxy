# tests/test_fib_par_range.py
from pathlib import Path
import types
import builtins
from paxy.assembler import assemble_file


def test_fib5_with_par_and_range(tmp_path: Path, capsys):
    src = tmp_path / "fib5.paxy"
    src.write_text(
        "SUB fib5 n\n"
        '  IF n "==" 0 ret\n'
        "  LET last 0\n"
        "  LET next 1\n"
        "  RANGE _ 1 n\n"
        '    LET t last "+" next\n'
        "    PAR last next  next  t\n"
        "  RANGEEND\n"
        "  LABEL ret\n"
        "  RETURN next\n"
        "SUBEND\n"
        "INPUT n\n"
        "GOSUB ans fib5 n\n"
        "PRINT ans\n"
    )

    # mock input("...") -> "10" (fib(10) = 55)
    orig_input = builtins.input
    builtins.input = lambda *a, **k: "10"
    try:
        code = assemble_file(src)
        g = {}
        types.FunctionType(code, g)()  # execute module
    finally:
        builtins.input = orig_input

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured[-1] == "55"
