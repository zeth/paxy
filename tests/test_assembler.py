# tests/test_assembler.py
from pathlib import Path
from types import CodeType
import importlib.util
import sys
import pytest

from paxy.cli import assemble_file
from paxy.cli import compile_file


def test_assemble_file_returns_codeobject(tmp_path: Path):
    src = tmp_path / "hello.paxy"
    src.write_text("PNT 'hello'\n")
    code = assemble_file(src)
    assert isinstance(code, CodeType)


def test_exec_prints_hello(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    src = tmp_path / "hello.paxy"
    src.write_text("PNT 'hello'\n")
    code = assemble_file(src)

    g = {"__name__": "__main__"}
    exec(code, g)

    out = capsys.readouterr().out
    assert out == "hello\n"


def test_compile_file_writes_pyc_and_is_importable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    src = tmp_path / "hello.paxy"
    src.write_text("PNT 'hello'\n")

    pyc_path = compile_file(src)
    assert pyc_path.exists()
    assert pyc_path.name == "hello.pyc"

    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("hello", None)

    spec = importlib.util.find_spec("hello")
    assert spec is not None

    # capture import-time output
    import builtins

    printed = []
    orig_print = builtins.print
    try:
        builtins.print = lambda *a, **k: printed.append(" ".join(map(str, a)))
        mod = importlib.import_module("hello")
    finally:
        builtins.print = orig_print

    assert printed == ["hello"]
    assert mod is not None
