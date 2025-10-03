# cli.py
import argparse
import os
import sys
import importlib.util
from importlib.machinery import SourcelessFileLoader
import sys, time
from pathlib import Path
import importlib._bootstrap_external as _be
from typing import List
from types import CodeType
import dis

from bytecode import Bytecode, Instr, CompilerFlags
from paxy.compiler.assembler import Assembler
from paxy.compiler.debug import debug_dump, emit_debugdis
from paxy.compiler.ir import ParsedItem
from paxy.compiler.twelve import (
    poptop_for_twelve,
)
from paxy.compiler.parser import Parser


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


def assemble_file(src_path: Path) -> CodeType:
    """
    Parse .paxy -> (ParsedItem stream) -> resolve labels -> Bytecode -> CodeType
    """
    parser = Parser()
    parsed: List[ParsedItem] = parser.parse_file(src_path)

    resolved = Assembler(parsed).resolve()
    debug_dump(resolved)  # <- one quiet line

    # Build final bytecode object
    bc = Bytecode(resolved)
    bc.filename = str(src_path)
    bc.name = "<module>"
    bc.flags |= CompilerFlags.NOFREE

    # First instruction lineno is used as first_lineno
    if resolved:
        first: Instr | None = next((x for x in resolved if isinstance(x, Instr)), None)
        if first is not None and first.lineno:
            bc.first_lineno = first.lineno

    code = poptop_for_twelve(bc)

    emit_debugdis(code)  # <- one quiet line to stderr (only if PAXY_DEBUG)
    return code


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


def run_pyc(path: str) -> None:
    """Load and execute a compiled .pyc file as if it were __main__."""
    base_loader = SourcelessFileLoader("__main__", path)
    spec = importlib.util.spec_from_file_location("__main__", path, loader=base_loader)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create import spec for {path!r}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["__main__"] = module

    # Narrow the loader type for mypy and execute the module.
    loader: importlib.abc.Loader = spec.loader
    loader.exec_module(module)


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

    # Compile to automatic CPython-style cache path
    if args.verbose:
        print(f"[paxy] compiling {src} ...")
    pyc_path = compile_file(src, optimization=args.optlevel)
    if args.verbose:
        print(f"[paxy] wrote {pyc_path}")

    if not args.compile_only:
        if args.verbose:
            print(f"[paxy] running {pyc_path}")
        run_pyc(str(pyc_path))
        if args.verbose:
            print("[paxy] done")


if __name__ == "__main__":
    main()
