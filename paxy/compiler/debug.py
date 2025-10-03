from pathlib import Path
import os, sys, io, dis
from contextlib import redirect_stdout
from types import CodeType
from bytecode import Bytecode

from paxy.compiler.twelve import (
    normalize_push_null_for_calls_312_seq,
)


def _dbg_enabled() -> bool:
    v = os.getenv("PAXY_DEBUG")
    return bool(v) and v != "0"


def _dbg_write(text: str) -> None:
    if not _dbg_enabled():
        return
    with open("/tmp/paxy_debug.txt", "a", encoding="utf-8") as fp:
        fp.write(text if text.endswith("\n") else text + "\n")


def debug(code_dbg: CodeType) -> str:
    if sys.version_info >= (3, 13):
        return dis.Bytecode(code_dbg).dis()
    buf = io.StringIO()
    with redirect_stdout(buf):
        dis.dis(code_dbg)
    return buf.getvalue()


def safe_disassemble(resolved_items) -> str:
    try:
        seq = normalize_push_null_for_calls_312_seq(list(resolved_items))
    except Exception:
        seq = list(resolved_items)

    try:
        bc_dbg = Bytecode(seq)
        return debug(bc_dbg.to_code())
    except Exception as exc:
        return f"<disassembly skipped: {exc}>"


def emit_debugdis(codeobj: CodeType, header: str = "== DISASSEMBLY ==") -> None:
    if not _dbg_enabled():
        return
    # write to stderr so tests that assert on stdout don't see it
    print(header, file=sys.stderr)
    print(debug(codeobj), file=sys.stderr)


def debug_dump(resolved) -> None:
    """
    Append a human-friendly dump of resolved instructions AND a safe disassembly
    to /tmp/paxy_debug.txt — but only when PAXY_DEBUG is set.
    """
    if not _dbg_enabled():
        return

    lines = ["== RESOLVED =="]
    for i, obj in enumerate(resolved):
        lines.append(f"{i:03d}: {obj!r}")
    lines.append("== DISASSEMBLY ==")
    lines.append(safe_disassemble(resolved))

    out_path = Path(os.getenv("PAXY_DEBUG_OUT", "/tmp/paxy_debug.txt"))
    out_path.write_text("\n".join(lines))
