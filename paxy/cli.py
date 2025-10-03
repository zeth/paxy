# paxy/cli.py (or wherever your CLI entry lives)

from __future__ import annotations
from pathlib import Path
from types import CodeType
from typing import Dict, Optional

from bytecode import Bytecode, Instr, CompilerFlags
from paxy.compiler.parser import Parser
from paxy.compiler.assembler import Assembler
from paxy.compiler.twelve import transpile_for_twelve
from paxy.compiler.debug import debug_dump, emit_debugdis

import importlib._bootstrap_external as _be
import marshal
import sys
import time


class PaxyCompiler:
    """Single-source compiler pipeline: parse -> assemble -> bytecode -> code."""

    def __init__(self, path: Path, *, verbose: bool = False, no_cache=False) -> None:
        self.path = Path(path)
        self.verbose = verbose
        self.no_cache = no_cache

    # ---------- core ----------
    def assemble(self) -> CodeType:
        parsed = Parser().parse_file(self.path)
        resolved = Assembler(parsed).resolve()
        debug_dump(resolved)

        bc = Bytecode(resolved)
        bc.filename = str(self.path)
        bc.name = "<module>"
        bc.flags |= CompilerFlags.NOFREE

        # First lineno, if present
        first_instr = next(
            (i for i in resolved if isinstance(i, Instr) and i.lineno), None
        )
        if first_instr:
            bc.first_lineno = first_instr.lineno

        code = transpile_for_twelve(bc)
        emit_debugdis(code)
        return code

    # ---------- .pyc I/O (optional helpers) ----------
    def pyc_path(self, *, optimization: Optional[int] = None) -> Path:
        tag = sys.implementation.cache_tag or "cpython"
        opt = f".opt-{optimization}" if optimization else ""
        return (
            self.path.with_suffix("")
            .with_name(f"{self.path.stem}.{tag}{opt}.pyc")
            .with_suffix(".pyc")
            .with_name(f"{self.path.stem}.{tag}{opt}.pyc")
            .parent
            / "__pycache__"
            / f"{self.path.stem}.{tag}{opt}.pyc"
        )

    def compile_pyc(
        self, *, hash_based: bool = False, optimization: Optional[int] = None
    ) -> Path:
        code = self.assemble()
        out = self.pyc_path(optimization=optimization)
        out.parent.mkdir(parents=True, exist_ok=True)

        if hash_based:
            src_bytes = self.path.read_bytes()
            # Hash-based pyc (checked=True)
            h = _be._source_hash(src_bytes)
            data = bytearray(_be.MAGIC_NUMBER)
            flags = 0b1 | (1 << 1)  # hash-based + checked
            data.extend(_be._pack_uint32(flags))
            data.extend(h)
            data.extend(marshal.dumps(code))
        else:
            # Timestamp-based pyc (mtime=now, size=0 since we don’t have a .py)
            ts = int(time.time())
            data = _be._code_to_timestamp_pyc(code, ts, 0)

        _be._write_atomic(str(out), data, mode=0o644)
        return out

    # ---------- run helpers ----------
    def run(self, g: Optional[Dict[str, object]] = None) -> None:
        g = {"__name__": "__main__"} if g is None else g
        exec(self.assemble(), g)

    def run_pyc(self, pyc: Path, g: Optional[Dict[str, object]] = None) -> None:
        g = {"__name__": "__main__"} if g is None else g
        # Very small reader for hash- or timestamp-based pyc
        with open(pyc, "rb") as f:
            data = f.read()
        # Skip header and load; importlib handles validation when importing modules,
        # but here we just trust the file we wrote.
        # MAGIC (4) + flags/timestamp (4) + hash/size (8) = 16 bytes header.
        code = marshal.loads(memoryview(data)[16:])
        exec(code, g)


# ---------- tiny wrappers to keep existing tests working ----------
def assemble_file(path: Path) -> CodeType:
    return PaxyCompiler(path).assemble()


def compile_paxy_to_pyc(path: Path, *, hash_based: bool = False) -> Path:
    return PaxyCompiler(path).compile_pyc(hash_based=hash_based)


def run_paxy_path(path: Path) -> None:
    PaxyCompiler(path).run()


# ---------- main stays slim ----------
def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="paxy")
    ap.add_argument("source", help="Path to .paxy program")
    ap.add_argument("--compile-only", action="store_true")
    ap.add_argument("--hash-based", action="store_true")
    ap.add_argument("-O", dest="optlevel", type=int, default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    c = PaxyCompiler(Path(args.source), verbose=args.verbose)
    if args.compile_only:
        out = c.compile_pyc(hash_based=args.hash_based, optimization=args.optlevel)
        if args.verbose:
            print(out)
        return 0

    # Run directly (no caching) to match test expectations
    c.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
