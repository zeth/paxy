import types
from pathlib import Path
from paxy.cli import assemble_file


def _run(src: str):
    tmp = Path(".__tmp_convert.paxy")
    tmp.write_text(src)
    try:
        code = assemble_file(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    g: dict[str, object] = {}
    types.FunctionType(code, g)()
    return g


def test_toint_from_float_truncates():
    g = _run("LET x 3.9\nTIN n x\n")
    assert g.get("n") == 3


def test_toint_from_string():
    g = _run('TIN n "42"\n')
    assert g.get("n") == 42


def test_tofloat_and_tostr():
    g = _run('TFL f "3.5"\nTST s 99\n')
    assert g.get("f") == 3.5
    assert g.get("s") == "99"


def test_pipeline_with_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "10")
    g = _run("INP n\nTIN n n\nLET ans n + 32\n")
    assert g.get("ans") == 42
