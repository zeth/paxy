# tests/test_cli.py
import sys
from pathlib import Path

import pytest

import paxy.cli as cli


def _fake_compile_file_factory(tmp_path, expected_opt=None):
    """Return (fake_func, calls_dict). Records args; returns a fake .pyc path."""
    calls = {"args": []}

    def fake_compile_file(src, *, optimization=None, **kwargs):
        calls["args"].append((src, optimization))
        # Emit a plausible .pyc path
        src_path = Path(src)
        pyc = tmp_path / f"{src_path.stem}.pyc"
        pyc.write_bytes(b"\x00")  # dummy file; we won't actually load it here
        return pyc

    if expected_opt is not None:
        # optional: enforce optimization expectation
        orig = fake_compile_file

        def wrapped(src, *, optimization=None, **kwargs):
            assert optimization == expected_opt
            return orig(src, optimization=optimization, **kwargs)

        return wrapped, calls

    return fake_compile_file, calls


def _fake_run_pyc_factory():
    """Return (fake_func, calls_list). Records the path it was asked to run."""
    calls = []

    def fake_run_pyc(path):
        calls.append(path)

    return fake_run_pyc, calls


def test_compile_only_calls_compile_not_run(monkeypatch, tmp_path):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    fake_compile, compile_calls = _fake_compile_file_factory(tmp_path)
    fake_run, run_calls = _fake_run_pyc_factory()

    monkeypatch.setattr(cli, "compile_file", fake_compile)
    monkeypatch.setattr(cli, "run_pyc", fake_run)

    monkeypatch.setattr(sys, "argv", ["paxy", "-c", str(src)])

    cli.main()

    # compile called once with our source; run not called
    assert len(compile_calls["args"]) == 1
    assert compile_calls["args"][0][0] == str(src)
    assert run_calls == []


def test_default_compile_then_run(monkeypatch, tmp_path):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    fake_compile, compile_calls = _fake_compile_file_factory(tmp_path)
    fake_run, run_calls = _fake_run_pyc_factory()

    monkeypatch.setattr(cli, "compile_file", fake_compile)
    monkeypatch.setattr(cli, "run_pyc", fake_run)

    monkeypatch.setattr(sys, "argv", ["paxy", str(src)])

    cli.main()

    assert len(compile_calls["args"]) == 1
    # run called once with the path returned by compile_file
    assert len(run_calls) == 1
    returned_pyc = Path(run_calls[0])
    assert returned_pyc.name == "hello.pyc"
    assert returned_pyc.exists()


def test_verbose_output(monkeypatch, tmp_path, capsys):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    fake_compile, _ = _fake_compile_file_factory(tmp_path)
    fake_run, _ = _fake_run_pyc_factory()

    monkeypatch.setattr(cli, "compile_file", fake_compile)
    monkeypatch.setattr(cli, "run_pyc", fake_run)

    monkeypatch.setattr(sys, "argv", ["paxy", "-v", str(src)])

    cli.main()
    out = capsys.readouterr().out
    assert "[paxy] compiling" in out
    assert "[paxy] wrote" in out
    assert "[paxy] running" in out
    assert "[paxy] done" in out


def test_optlevel_passed_through(monkeypatch, tmp_path):
    src = tmp_path / "hello.paxy"
    src.write_text("")

    fake_compile, compile_calls = _fake_compile_file_factory(tmp_path, expected_opt=2)
    fake_run, _ = _fake_run_pyc_factory()

    monkeypatch.setattr(cli, "compile_file", fake_compile)
    monkeypatch.setattr(cli, "run_pyc", fake_run)

    monkeypatch.setattr(sys, "argv", ["paxy", "-O", "2", str(src)])

    cli.main()

    assert len(compile_calls["args"]) == 1
    _, opt = compile_calls["args"][0]
    assert opt == 2


def test_missing_source_exits(monkeypatch, tmp_path):
    missing = tmp_path / "does_not_exist.paxy"

    # Ensure compile/run aren't called if we bail early
    monkeypatch.setattr(cli, "compile_file", lambda *a, **k: pytest.fail("compile_file should not be called"))
    monkeypatch.setattr(cli, "run_pyc", lambda *a, **k: pytest.fail("run_pyc should not be called"))

    monkeypatch.setattr(sys, "argv", ["paxy", str(missing)])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    # sys.exit(message) stores the message in exc.value.code
    assert "source file" in str(exc.value)
