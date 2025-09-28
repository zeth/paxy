# tests/test_compiler.py
import importlib
import importlib.util
import sys
from pathlib import Path
import pytest
import paxy.cli as compiler


def _stub_code(filename: str):
    return compile("x = 1\n", filename, "exec")


def test_sourceless_writes_name_pyc_and_is_importable(monkeypatch, tmp_path):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    monkeypatch.setattr(compiler, "assemble_file", lambda path: _stub_code(str(path)))
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))  # <-- make tmp_path importable

    pyc_path = compiler.compile_file(src)
    assert pyc_path == tmp_path / "hello.pyc"
    assert pyc_path.exists()

    sys.modules.pop("hello", None)
    spec = importlib.util.find_spec("hello")
    assert spec is not None, "import system did not find hello.pyc"

    mod = importlib.import_module("hello")
    assert getattr(mod, "x", None) == 1


def test_with_py_exists_writes_cpython_cache_path(monkeypatch, tmp_path):
    src = tmp_path / "hello.paxy"
    src.write_text("")
    (tmp_path / "hello.py").write_text("print('source present')\n")

    monkeypatch.setattr(compiler, "assemble_file", lambda path: _stub_code(str(path)))
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))  # <-- ensure tmp_path is on sys.path

    pyc_path = compiler.compile_file(src)
    tag = sys.implementation.cache_tag
    expected = tmp_path / "__pycache__" / f"hello.{tag}.pyc"
    assert pyc_path == expected
    assert pyc_path.exists()

    sys.modules.pop("hello", None)
    spec = importlib.util.find_spec("hello")
    assert spec is not None, "import system did not find hello module (via source)"
