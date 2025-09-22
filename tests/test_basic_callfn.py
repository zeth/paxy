from pathlib import Path
import pytest
from paxy.parser import Parser

def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]

def strip_leading_resume(pairs):
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    return out

def canon_argless(pairs):
    out = []
    for n, a in pairs:
        if n in {"PUSH_NULL", "POP_TOP"}:
            out.append((n, 0))
        else:
            out.append((n, a))
    return out

def test_callfn_lowers_to_zero_arg_call(tmp_path: Path):
    src = tmp_path / "prog.paxy"
    src.write_text("CALLFN dir\nRETURN_CONST None\n")
    got = canon_argless(strip_leading_resume(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "dir"),
        ("PUSH_NULL", 0),
        ("CALL", 0),
        ("POP_TOP", 0),
        ("RETURN_CONST", None),
    ]

def test_callfn_runtime_calls_global_function(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    # We’ll call a function injected into globals that prints "ok"
    src = tmp_path / "prog2.paxy"
    src.write_text("CALLFN zap\n")

    instrs = Parser().parse_file(src)

    from bytecode import Bytecode, CompilerFlags
    bc = Bytecode(instrs)
    bc.flags |= CompilerFlags.NOFREE
    code = bc.to_code()

    g = {"__name__": "__main__", "zap": lambda: print("ok")}
    exec(code, g)
    assert capsys.readouterr().out == "ok\n"

def test_callfn_errors(tmp_path: Path):
    src = tmp_path / "bad1.paxy"
    src.write_text("CALLFN\n")
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert "takes exactly one identifier" in str(exc.value)

    src.write_text("CALLFN 'zap'\n")
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert "expects an identifier" in str(exc.value)

    src.write_text("CALLFN a b\n")
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert "takes exactly one identifier" in str(exc.value)
