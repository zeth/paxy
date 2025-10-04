from __future__ import annotations
from pathlib import Path
from typing import Optional
import argparse
from paxy.compiler.compile import PaxyCompiler


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="paxy")
    ap.add_argument("source", help="Path to .paxy program")
    ap.add_argument(
        "--compile-only", action="store_true", help="Only compile to .pyc, do not run"
    )
    ap.add_argument(
        "--hash-based", action="store_true", help="Write hash-based pyc (default)"
    )
    ap.add_argument(
        "-O",
        dest="optlevel",
        type=int,
        default=None,
        help="Optimization suffix in filename (.opt-1 or .opt-2); filename only",
    )
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
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
