# cli.py
import argparse
import os
import sys
import importlib.util
from importlib.machinery import SourcelessFileLoader

from .compiler import compile_file


def run_pyc(path: str) -> None:
    """Load and execute a compiled .pyc file as if it were __main__."""
    loader = SourcelessFileLoader("__main__", path)
    spec = importlib.util.spec_from_file_location("__main__", path, loader=loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["__main__"] = module
    loader.exec_module(module)


def main():
    parser = argparse.ArgumentParser(
        prog="paxy",
        description="Paxy: BASIC-like language that compiles to Python .pyc"
    )
    parser.add_argument("source", help="Paxy source file (.paxy)")
    parser.add_argument(
        "-c", "--compile-only",
        action="store_true",
        help="Only compile to .pyc, do not run"
    )
    parser.add_argument(
        "-O",
        dest="optlevel",
        type=int,
        choices=(1, 2),
        help="Optimization suffix in filename (.opt-1 or .opt-2); filename only"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
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
