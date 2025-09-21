# tests/test_assembler.py
import types
from pathlib import Path

import pytest

from paxy.assembler import assemble_file


def test_returns_code_object(tmp_path):
    src = tmp_path / "hello.paxy"
    src.write_text("")  # content irrelevant to the stub
    code = assemble_file(src)
    assert isinstance(code, types.CodeType)


def test_exec_prints_hello(tmp_path, capsys):
    src = tmp_path / "hello.paxy"
    src.write_text("")
    code = assemble_file(src)

    # Execute as a module: give it its own globals dict
    g = {"__name__": "__main__"}
    exec(code, g, None)

    out = capsys.readouterr().out
    assert out == "hello\n"


def test_filename_is_src_path(tmp_path):
    src = tmp_path / "myprog.paxy"
    src.write_text("")
    code = assemble_file(src)

    # co_filename should equal the string we passed to compile()
    assert code.co_filename == str(src)
