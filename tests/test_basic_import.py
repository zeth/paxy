from pathlib import Path
import sys
from paxy.compiler.parser import Parser
from tests.helpers import run_paxy_path


def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]


def strip_leading_resume(pairs):
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    return out


def canon_argless(pairs):
    out = []
    for n, a in pairs:
        if n in {"PUSH_NULL", "POP_TOP", "RETURN_VALUE"}:
            out.append((n, 0))
        else:
            out.append((n, a))
    return out


def test_import_lowers_via___import__(tmp_path: Path):
    src = tmp_path / "prog.paxy"
    src.write_text("IMP 'time'\nLOAD_CONST None\nRETURN_VALUE\n")
    got = canon_argless(strip_leading_resume(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "__import__"),
        ("PUSH_NULL", 0),
        ("LOAD_CONST", "time"),
        ("CALL", 1),
        ("POP_TOP", 0),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", 0),
    ]


def test_import_runtime_populates_sys_modules(tmp_path: Path):
    modname = "time"
    # Ensure it’s present to start; then remove to prove __import__ side effect
    sys.modules.pop(modname, None)

    src = tmp_path / "prog2.paxy"
    src.write_text("IMP 'time'\n")
    run_paxy_path(src)

    assert modname in sys.modules
