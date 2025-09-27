# compiler.py
from __future__ import annotations
import sys, time
from pathlib import Path
import importlib._bootstrap_external as _be
from paxy.assembler import assemble_file


class PaxyCompileError(RuntimeError):
    pass


def output_path_for(src: str | Path, *, optimization: int | None = None) -> Path:
    """
    If a sibling .py exists -> CPython cache path in __pycache__/ with tag.
    Else (sourceless)       -> tagless <name>.pyc next to the source.
    """
    src = Path(src)
    base = src.stem
    py_sibling = src.with_suffix(".py")
    if py_sibling.exists():
        tag = sys.implementation.cache_tag  # e.g. 'cpython-313'
        opt = f".opt-{optimization}" if optimization else ""
        return src.parent / "__pycache__" / f"{base}.{tag}{opt}.pyc"
    else:
        # sourceless import path that the importer will actually check
        return src.parent / f"{base}.pyc"


def compile_file(
    src: str | Path,
    *,
    optimization: int | None = None,
    hash_based: bool = False,
    mtime: int | None = None,
    mode: int = 0o644,
) -> Path:
    src_p = Path(src)
    dest_p = output_path_for(src_p, optimization=optimization)

    try:
        code = assemble_file(src_p)
    except Exception as exc:
        raise PaxyCompileError(f"assembly failed for {src_p}: {exc}") from exc

    try:
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        if hash_based:
            pyc = _be._code_to_hash_pyc(code, checked_hash=None)
        else:
            ts = int(time.time()) if mtime is None else int(mtime)
            pyc = _be._code_to_timestamp_pyc(code, ts, 0)  # size=0 for sourceless
        _be._write_atomic(str(dest_p), pyc, mode=mode)
    except Exception as exc:
        raise PaxyCompileError(f"writing .pyc failed for {dest_p}: {exc}") from exc

    return dest_p
