from __future__ import annotations
from pathlib import Path
from types import CodeType, ModuleType
from typing import Dict, Optional
import argparse

from importlib._bootstrap_external import (
    MAGIC_NUMBER,
    _pack_uint32 as pack,
    _code_to_timestamp_pyc as code_to_timestamp_pyc,
    _write_atomic as write_atomic,
)
from importlib.util import source_hash
import marshal
import struct
import sys
from bytecode import Bytecode, Instr, CompilerFlags
from paxy.compiler.parser import Parser
from paxy.compiler.assembler import Assembler
from paxy.compiler.twelve import transpile_for_twelve
from paxy.compiler.debug import debug_dump, emit_debugdis


class PaxyCompiler:
    """Single-source compiler pipeline:
    parse -> assemble -> bytecode -> code (+ optional .pyc cache)."""

    def __init__(
        self, path: Path, *, verbose: bool = False, no_cache: bool = False
    ) -> None:
        self.path = Path(path)
        self.verbose = verbose
        self.no_cache = no_cache

    # ---------- core ----------
    def assemble(self) -> CodeType:
        # Try cache first (unless disabled)
        if not self.no_cache:
            cached = self._load_from_cache()
            if cached is not None:
                return cached

        # Compile fresh
        parsed = Parser().parse_file(self.path)
        resolved = Assembler(parsed).resolve()
        debug_dump(resolved)

        bc = Bytecode(resolved)
        bc.filename = str(self.path)
        bc.name = "<module>"
        bc.flags |= CompilerFlags.NOFREE

        # first_lineno if present
        first_instr = next(
            (i for i in resolved if isinstance(i, Instr) and i.lineno), None
        )
        if first_instr:
            bc.first_lineno = first_instr.lineno

        code = transpile_for_twelve(bc)
        emit_debugdis(code)

        # Write cache unless disabled
        if not self.no_cache:
            self._write_cache(code)

        return code

    # ---------- .pyc paths ----------
    def pyc_path(self, *, optimization: Optional[int] = None) -> Path:
        """
        Where to write/read the .pyc for this .paxy source.

        - If a sibling hello.py exists => use PEP 3147 layout:
                __pycache__/hello.<tag>[.opt-N].pyc
        - Otherwise (sourceless) => write a top-level hello.pyc
            so the import system can find it by name.
        """
        src_py = self.path.with_suffix(".py")
        if not src_py.exists():  # sourceless case
            return self.path.with_suffix(".pyc")  # top-level hello.pyc

        tag = sys.implementation.cache_tag or "cpython"
        opt = f".opt-{optimization}" if optimization else ""
        cache_dir = self.path.parent / "__pycache__"
        return cache_dir / f"{self.path.stem}.{tag}{opt}.pyc"

    # ---------- cache I/O ----------
    def _source_hash(self) -> bytes:
        # Hash of the *paxy* source bytes
        return source_hash(self.path.read_bytes())

    def _write_cache(
        self, code: CodeType, *, optimization: Optional[int] = None
    ) -> None:
        """Write a PEP 552 hash-based pyc (checked=True)."""
        out = self.pyc_path(optimization=optimization)
        out.parent.mkdir(parents=True, exist_ok=True)

        h = self._source_hash()
        # MAGIC (4) + FLAGS (4) + HASH (8) + marshal(code)
        data = bytearray(MAGIC_NUMBER)
        flags = 0b1 | (1 << 1)  # hash-based + checked
        data.extend(pack(flags))
        data.extend(h)
        data.extend(marshal.dumps(code))
        write_atomic(str(out), data, mode=0o644)

    def _load_from_cache(
        self, *, optimization: Optional[int] = None
    ) -> Optional[CodeType]:
        """Return cached CodeType if a hash-based pyc matches current source hash."""
        pyc = self.pyc_path(optimization=optimization)
        if not pyc.is_file():
            return None

        try:
            data = memoryview(pyc.read_bytes())
            # Basic sanity on MAGIC
            if bytes(data[:4]) != MAGIC_NUMBER:
                return None

            word = struct.unpack("<I", data[4:8])[0]
            if word & 0b1:
                # hash-based header: FLAGS + HASH
                cached_hash = bytes(data[8:16])
                if cached_hash != self._source_hash():
                    return None
                code = marshal.loads(data[16:])
                return code  # cache hit

            # timestamp-based header (we don't write these, but be forgiving)
            # MAGIC + TIMESTAMP (4) + SIZE (4)
            mtime = word
            size = struct.unpack("<I", data[8:12])[0]
            st = self.path.stat()
            if int(st.st_mtime) != mtime or st.st_size != size:
                return None
            code = marshal.loads(data[12:])
            return code
        except (OSError, EOFError, ValueError, TypeError, struct.error):
            # OSError: file disappeared between is_file() and read_bytes() or stat race.
            # struct.error: header too short / malformed.
            # EOFError, ValueError, TypeError: marshal.loads on
            # truncated/invalid data or wrong type.
            return None

    def _exec_globals(self, g: Optional[dict[str, object]] = None) -> dict[str, object]:
        """
        Create or merge an execution globals dict with import-style metadata:
        __name__, __file__, __package__, __spec__, __loader__.

        If no dict is provided, build a proper __main__ module and register it
        in sys.modules. If a dict is provided, only fill missing fields—don’t
        overwrite anything the caller set.
        """
        if g is None:
            mod = ModuleType("__main__")
            mod.__file__ = str(self.path)
            mod.__package__ = None
            mod.__spec__ = None
            mod.__loader__ = None
            sys.modules["__main__"] = mod
            return mod.__dict__

        # Merge defaults without clobbering caller-provided values.
        g.setdefault("__name__", "__main__")
        g.setdefault("__file__", str(self.path))
        g.setdefault("__package__", None)
        g.setdefault("__spec__", None)
        g.setdefault("__loader__", None)
        return g

    def run(self, g: Optional[dict[str, object]] = None) -> None:
        """Assemble and execute the program."""
        exec(self.assemble(), self._exec_globals(g))

    def compile_pyc(
        self, *, hash_based: bool = True, optimization: Optional[int] = None
    ) -> Path:
        """Explicit compiler to .pyc; default is hash-based (PEP 552)."""
        code = self.assemble()
        out = self.pyc_path(optimization=optimization)
        out.parent.mkdir(parents=True, exist_ok=True)

        if hash_based:
            self._write_cache(code, optimization=optimization)
        else:
            # timestamp-based for completeness
            st = self.path.stat()
            data = code_to_timestamp_pyc(code, int(st.st_mtime), st.st_size)
            write_atomic(str(out), data, mode=0o644)
        return out


# ---------- tiny wrappers to keep existing tests working ----------
def assemble_file(path: Path, *, no_cache: bool = False) -> CodeType:
    """Tests can pass no_cache=True to force a fresh compile and avoid writing a pyc."""
    return PaxyCompiler(path, no_cache=no_cache).assemble()


def compile_file(path: Path, *, hash_based: bool = True) -> Path:
    return PaxyCompiler(path).compile_pyc(hash_based=hash_based)


def run_pyc(path: Path, *, no_cache: bool = False) -> None:
    PaxyCompiler(path, no_cache=no_cache).run()


# ---------- main stays slim ----------
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="paxy")
    ap.add_argument("source", help="Path to .paxy program")
    ap.add_argument("--compile-only", action="store_true")
    ap.add_argument(
        "--hash-based", action="store_true", help="Write hash-based pyc (default)"
    )
    ap.add_argument("-O", dest="optlevel", type=int, default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument(
        "--no-cache", action="store_true", help="Bypass cache and do not write .pyc"
    )
    args = ap.parse_args(argv)

    c = PaxyCompiler(Path(args.source), verbose=args.verbose, no_cache=args.no_cache)

    if args.compile_only:
        out = c.compile_pyc(hash_based=args.hash_based, optimization=args.optlevel)
        if args.verbose:
            print(out)
        return 0

    c.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
