# compiler.py
from __future__ import annotations

import time
import sys
from pathlib import Path
import importlib._bootstrap_external as _be

from .assembler import assemble_file  # must return a types.CodeType


class PaxyCompileError(RuntimeError):
    pass


def cache_path_for(src: str | Path, *, optimization: int | None = None) -> Path:
    """
    CPython-style cache name for *Paxy* source:
    <dir>/__pycache__/<stem>.<cache_tag>[.opt-N].pyc
    """
    src = Path(src)
    tag = sys.implementation.cache_tag  # e.g. 'cpython-311'
    opt = f".opt-{optimization}" if optimization else ""
    return src.parent / "__pycache__" / f"{src.stem}.{tag}{opt}.pyc"


def compile_file(
    src: str | Path,
    *,
    optimization: int | None = None,
    hash_based: bool = False,
    mtime: int | None = None,
    mode: int = 0o644,
) -> Path:
    """
    Compile a .paxy source file to a sourceless .pyc at the CPython-style cache path.
    Returns the Path to the written .pyc.
    """
    src_p = Path(src)
    dest_p = cache_path_for(src_p, optimization=optimization)

    try:
        code = assemble_file(src_p)  # -> types.CodeType for the module
    except Exception as exc:
        raise PaxyCompileError(f"assembly failed for {src_p}: {exc}") from exc

    try:
        dest_p.parent.mkdir(parents=True, exist_ok=True)

        if hash_based:
            pyc_bytes = _be._code_to_hash_pyc(code, checked_hash=None)
        else:
            ts = int(time.time()) if mtime is None else int(mtime)
            # IMPORTANT: for sourceless .pyc, size must be 0
            pyc_bytes = _be._code_to_timestamp_pyc(code, ts, 0)

        _be._write_atomic(str(dest_p), pyc_bytes, mode=mode)
    except Exception as exc:
        raise PaxyCompileError(f"writing .pyc failed for {dest_p}: {exc}") from exc

    return dest_p
