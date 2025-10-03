# paxy/cli.py
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from types import CodeType
import time
import marshal
import importlib.util as importlib_util
import importlib._bootstrap_external as bootstrap
from importlib.machinery import SourcelessFileLoader
from typing import Iterable

from bytecode import Bytecode, Instr, CompilerFlags

from paxy.compiler.parser import Parser
from paxy.compiler.ir import ParsedItem
from paxy.compiler.assembler import Assembler
from paxy.compiler.twelve import poptop_for_twelve
from paxy.compiler.debug import debug_dump, emit_debugdis


class PaxyCompileError(RuntimeError):
    """Raised when assembly / compile fails."""


class PaxyCompiler:
    """
    All the non-CLI bits for parsing, assembling, caching and running .paxy files.
    """

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose

    # ---------- public API ----------

    def assemble_file(self, src_path: Path) -> CodeType:
        """
        Parse .paxy -> resolve -> Bytecode -> CodeType (3.12-compatible).
        Also emits optional debug (stderr) via paxy.compiler.debug.
        """
        parsed = Parser().parse_file(src_path)
        resolved = Assembler(parsed).resolve()
        debug_dump(resolved)

        bc = Bytecode(resolved)
        bc.filename = str(src_path)
        bc.name = "<module>"
        bc.flags |= CompilerFlags.NOFREE

        # First instruction's lineno => first_lineno (helps disassembly look nice)
        first_instr = next((i for i in resolved if isinstance(i, Instr)), None)
        if first_instr and first_instr.lineno:
            bc.first_lineno = first_instr.lineno

        code = poptop_for_twelve(bc)
        emit_debugdis(code)
        return code

    def compile_file(
        self,
        src: str | Path,
        *,
        optimization: int | None = None,
        hash_based: bool = False,
        mtime: int | None = None,
        mode: int = 0o644,
    ) -> Path:
        """
        Compile a .paxy file to a CPython-style .pyc (in __pycache__ if a .py sibling exists).
        By default produces timestamp-based pyc (like normal Python).
        Set hash_based=True to write a checked hash-based pyc.
        """
        src_p = Path(src)
        dest_p = self.output_path_for(src_p, optimization=optimization)

        try:
            # Try to reuse a valid hash-based cache if present
            code = self._load_code_with_cache(src_p)
        except Exception as exc:  # pragma: no cover (bubble up nicely)
            raise PaxyCompileError(f"assembly failed for {src_p}: {exc}") from exc

        try:
            dest_p.parent.mkdir(parents=True, exist_ok=True)
            if hash_based:
                src_bytes = src_p.read_bytes()
                pyc = self._make_hash_pyc(code, src_bytes, checked=True)
            else:
                ts = int(time.time()) if mtime is None else int(mtime)
                # size=0 is fine for sourceless (we’re not mirroring .py size)
                pyc = bootstrap._code_to_timestamp_pyc(code, ts, 0)
            bootstrap._write_atomic(str(dest_p), pyc, mode=mode)
        except Exception as exc:  # pragma: no cover
            raise PaxyCompileError(f"writing .pyc failed for {dest_p}: {exc}") from exc

        return dest_p

    def run_pyc(self, path: str) -> None:
        """Execute a compiled .pyc as __main__ (mirrors Python’s loader behavior)."""
        loader = SourcelessFileLoader("__main__", path)
        spec = importlib_util.spec_from_file_location("__main__", path, loader=loader)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not create import spec for {path!r}")
        module = importlib_util.module_from_spec(spec)
        sys.modules["__main__"] = module
        spec.loader.exec_module(module)

    def output_path_for(
        self, src: str | Path, *, optimization: int | None = None
    ) -> Path:
        """
        If a sibling .py exists -> CPython cache path in __pycache__/ with tag.
        Else (sourceless)       -> <name>.pyc next to the source.
        """
        src = Path(src)
        base = src.stem
        py_sibling = src.with_suffix(".py")
        if py_sibling.exists():
            tag = sys.implementation.cache_tag  # e.g. 'cpython-312'
            opt = f".opt-{optimization}" if optimization else ""
            return src.parent / "__pycache__" / f"{base}.{tag}{opt}.pyc"
        return src.parent / f"{base}.pyc"

    # ---------- thin wrappers to keep existing imports working ----------

    # These mirror the old module-level functions used in tests.

    def load_code(self, src_path: Path) -> CodeType:
        """Public convenience: assemble and write a hash-checked cache next to src if valid is absent."""
        return self._load_code_with_cache(src_path)

    # ---------- internals ----------

    def _load_code_with_cache(self, src_path: Path) -> CodeType:
        """
        Try to load from a *hash-based* pyc cache (if present & matches source bytes).
        If missing or mismatched, assemble and write a fresh checked hash-based cache,
        then return the new code object.
        """
        src_bytes = src_path.read_bytes()

        # Use the canonical location Python would choose for a source file
        pyc_path = Path(bootstrap.cache_from_source(str(src_path)))
        cached = self._load_hash_pyc_if_valid(pyc_path, src_bytes)
        if cached is not None:
            if self.verbose:
                print(f"[paxy] using cache {pyc_path}")
            return cached

        # Assemble and write a fresh checked-hash pyc so next run can reuse it
        code = self.assemble_file(src_path)
        pyc_data = self._make_hash_pyc(code, src_bytes, checked=True)
        pyc_path.parent.mkdir(parents=True, exist_ok=True)
        bootstrap._write_atomic(str(pyc_path), pyc_data)
        return code

    @staticmethod
    def _make_hash_pyc(
        code: CodeType, src_bytes: bytes, *, checked: bool = True
    ) -> bytes:
        """Create a checked hash-based .pyc payload for given code+source."""
        src_hash = importlib_util.source_hash(src_bytes)  # 8 bytes
        return bootstrap._code_to_hash_pyc(code, src_hash, checked=checked)

    @staticmethod
    def _load_hash_pyc_if_valid(pyc_path: Path, src_bytes: bytes) -> CodeType | None:
        """Return code object from a hash-based .pyc if its 8-byte hash matches src_bytes; else None."""
        try:
            data = pyc_path.read_bytes()
        except FileNotFoundError:
            return None

        if data[:4] != bootstrap.MAGIC_NUMBER:
            return None

        flags = int.from_bytes(data[4:8], "little")
        is_hash = bool(flags & 0b1)
        if not is_hash:
            return None

        stored = data[8:16]  # 8-byte hash
        wanted = importlib_util.source_hash(src_bytes)
        if stored != wanted:
            return None

        # The remainder is marshal.dumps(code)
        return marshal.loads(data[16:])


# --------------------------------------------------------------------------------------
# Back-compat: keep simple module-level helpers that delegate to a default instance.
# (This lets existing tests keep doing `from paxy.cli import assemble_file`, etc.)
# --------------------------------------------------------------------------------------

_default = PaxyCompiler(verbose=False)


def assemble_file(src_path: Path) -> CodeType:
    return _default.assemble_file(src_path)


def compile_file(
    src: str | Path,
    *,
    optimization: int | None = None,
    hash_based: bool = False,
    mtime: int | None = None,
    mode: int = 0o644,
) -> Path:
    return _default.compile_file(
        src,
        optimization=optimization,
        hash_based=hash_based,
        mtime=mtime,
        mode=mode,
    )


def run_pyc(path: str) -> None:
    return _default.run_pyc(path)


# --------------------------------------------------------------------------------------
# CLI (argparse) kept minimal, per your request.
# --------------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="paxy",
        description="Paxy: BASIC-like language that compiles to Python .pyc",
    )
    parser.add_argument("source", help="Paxy source file (.paxy)")
    parser.add_argument(
        "-c",
        "--compile-only",
        action="store_true",
        help="Only compile to .pyc, do not run",
    )
    parser.add_argument(
        "-O",
        dest="optlevel",
        type=int,
        choices=(1, 2),
        help="Optimization suffix in filename (.opt-1 or .opt-2); filename only",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    src = args.source
    if not os.path.exists(src):
        sys.exit(f"error: source file {src} not found")

    compiler = PaxyCompiler(verbose=args.verbose)

    if args.verbose:
        print(f"[paxy] compiling {src} ...")
    pyc_path = compiler.compile_file(src, optimization=args.optlevel)
    if args.verbose:
        print(f"[paxy] wrote {pyc_path}")

    if not args.compile_only:
        if args.verbose:
            print(f"[paxy] running {pyc_path}")
        compiler.run_pyc(str(pyc_path))
        if args.verbose:
            print("[paxy] done")


if __name__ == "__main__":
    main()
