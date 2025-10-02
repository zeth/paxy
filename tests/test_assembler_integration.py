# tests/test_assembler_integration.py
from pathlib import Path
from types import CodeType
import importlib.util
import sys

import pytest

from paxy.cli import assemble_file
from paxy.cli import compile_file


PROGRAM = """\
RESUME 0
LOAD_NAME 'print'
PUSH_NULL
LOAD_CONST 'hello'
CALL 1
POP_TOP
LOAD_CONST None
RETURN_VALUE
"""


def test_assemble_file_returns_codeobject(tmp_path: Path):
    src = tmp_path / "hello.paxy"
    src.write_text(PROGRAM)

    code = assemble_file(src)
    assert isinstance(code, CodeType)


def test_assemble_file_executes_and_prints_hello(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    src = tmp_path / "hello.paxy"
    src.write_text(PROGRAM)

    code = assemble_file(src)
    g = {"__name__": "__main__"}
    exec(code, g)

    out = capsys.readouterr().out
    assert out == "hello\n"


def test_compile_file_writes_pyc_and_is_importable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """
    Full pipeline: assemble -> write sourceless .pyc -> import module.
    """
    src = tmp_path / "hello.paxy"
    src.write_text(PROGRAM)

    # Compile to sourceless pyc (should be <name>.pyc in the same dir)
    pyc_path = compile_file(src)
    assert pyc_path.exists()
    assert pyc_path.name == "hello.pyc"

    # Make tmp_path importable, clear any stale module
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("hello", None)

    # Import and smoke-check it runs (prints once on import)
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
