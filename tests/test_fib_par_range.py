from pathlib import Path
import types, builtins
from paxy.cli import assemble_file


def test_fib5_with_par_and_range(tmp_path, capsys):
    src = tmp_path / "fib5.paxy"
    src.write_text(
        "SUB fib5 n\n"
        '  IF n "==" 0 ret\n'
        "  LET last 0\n"
        "  LET next 1\n"
        "  RNG _ 1 n\n"
        '    LET t last "+" next\n'
        "    PAR last next  next  t\n"
        "  RNE\n"
        "  LBL ret\n"
        "  RET next\n"
        "SBE\n"
        "INP n\n"
        "GOS n int n\n"  # <- added coercion
        "GOS ans fib5 n\n"
        "PNT ans\n"
    )

    orig_input = builtins.input
    builtins.input = lambda *a, **k: "10"  # fib(10)=55
    try:
        code = assemble_file(src)
        g = {}
        types.FunctionType(code, g)()
    finally:
        builtins.input = orig_input

    out = capsys.readouterr().out.strip().splitlines()
    assert out[-1] == "55"
