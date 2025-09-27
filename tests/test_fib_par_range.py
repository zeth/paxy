from pathlib import Path
import types, builtins
from paxy.assembler import assemble_file


def test_fib5_with_par_and_range(tmp_path, capsys):
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
        "GOSUB n int n\n"  # <- added coercion
        "GOSUB ans fib5 n\n"
        "PRINT ans\n"
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
