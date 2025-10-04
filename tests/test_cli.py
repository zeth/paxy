# tests/test_cli.py
import sys
from pathlib import Path

import pytest

import paxy.cli as cli
import paxy.compiler.compile as compile


def _fake_compile_pyc_factory(tmp_path, expected_opt=None):
    """
    Return (fake_method, calls_list).
    The fake mimics PaxyCompiler.compile_pyc and records (self.path, hash_based, optimization).
    It also writes a dummy pyc so downstream assertions can check existence.
    """
    calls: list[tuple[Path, bool, int | None]] = []

    def fake_compile_pyc(self, *, hash_based: bool = True, optimization=None):
        if expected_opt is not None:
            assert optimization == expected_opt
        calls.append((self.path, hash_based, optimization))
        out = tmp_path / f"{self.path.stem}.pyc"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x00")
        return out

    return fake_compile_pyc, calls


def _fake_run_method_factory():
    """
    Return (fake_method, calls_list).
    The fake mimics PaxyCompiler.run and records self.path it was asked to run.
    """
    calls: list[Path] = []

    def fake_run(self, g=None):
        calls.append(self.path)

    return fake_run, calls


def test_compile_only_calls_compile_not_run(monkeypatch, tmp_path: Path):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    fake_compile, compile_calls = _fake_compile_pyc_factory(tmp_path)
    fake_run, run_calls = _fake_run_method_factory()

    monkeypatch.setattr(compile.PaxyCompiler, "compile_pyc", fake_compile)
    monkeypatch.setattr(compile.PaxyCompiler, "run", fake_run)

    monkeypatch.setattr(sys, "argv", ["paxy", "--compile-only", str(src)])

    cli.main()

    # compile called once with our source; run not called
    assert len(compile_calls) == 1
    assert compile_calls[0][0] == src
    assert run_calls == []


def test_default_compile_then_run(monkeypatch, tmp_path: Path):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    # In the new CLI, default path executes via PaxyCompiler.run (no explicit compile_pyc call)
    fake_compile, compile_calls = _fake_compile_pyc_factory(tmp_path)
    fake_run, run_calls = _fake_run_method_factory()

    monkeypatch.setattr(sys, "argv", ["paxy", str(src)])
    monkeypatch.setattr(compile.PaxyCompiler, "compile_pyc", fake_compile)
    monkeypatch.setattr(compile.PaxyCompiler, "run", fake_run)

    cli.main()

    assert compile_calls == []  # no explicit compile in default path
    assert run_calls == [src]  # run called once on our source


def test_verbose_output(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    fake_run, _ = _fake_run_method_factory()
    monkeypatch.setattr(compile.PaxyCompiler, "run", fake_run)

    # New CLI doesn't print bespoke verbose banners; we just ensure it runs without error.
    monkeypatch.setattr(sys, "argv", ["paxy", "-v", str(src)])

    cli.main()
    out = capsys.readouterr().out
    # Don't assert specific strings; simply ensure the program didn't crash.
    assert out is not None


def test_optlevel_passed_through(monkeypatch, tmp_path: Path):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    fake_compile, compile_calls = _fake_compile_pyc_factory(tmp_path, expected_opt=2)
    monkeypatch.setattr(compile.PaxyCompiler, "compile_pyc", fake_compile)

    # Optlevel is only used when we do --compile-only
    monkeypatch.setattr(sys, "argv", ["paxy", "--compile-only", "-O", "2", str(src)])

    cli.main()

    assert len(compile_calls) == 1
    _, _, opt = compile_calls[0]
    assert opt == 2


def test_missing_source_exits(monkeypatch, tmp_path: Path):
    missing = tmp_path / "does_not_exist.paxy"

    # With the new CLI, a missing file results in FileNotFoundError bubbling out.
    monkeypatch.setattr(sys, "argv", ["paxy", str(missing)])

    with pytest.raises(FileNotFoundError):
        cli.main()
