from pathlib import Path
import pytest

from paxy.parser import Parser
from paxy.assembler import assemble_file


def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]


def strip_leading_resume(pairs):
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    return out


def norm_argless(pairs):
    # normalize PUSH_NULL/POP_TOP arg to a token so 0/None/UNSET all compare equal
    def zeroish(x):
        if x is None:
            return 0
        v = getattr(x, "value", x)
        try:
            return 0 if int(v) == 0 else v
        except Exception:
            return v
    out = []
    for n, a in pairs:
        if n in {"PUSH_NULL", "POP_TOP"}:
            out.append((n, zeroish(a)))
        else:
            out.append((n, a))
    return out


def test_input_lowers_to_call_and_store(tmp_path: Path):
    src = tmp_path / "inp.paxy"
    src.write_text("INPUT x\nRETURN_CONST None\n")

    got = norm_argless(strip_leading_resume(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "input"),
        ("PUSH_NULL", 0),
        ("CALL", 0),
        ("STORE_NAME", "x"),
        ("RETURN_CONST", None),
    ]


def test_input_runtime_reads_and_stores_string(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Program: read into x, then print x to prove value is there
    src = tmp_path / "inp2.paxy"
    src.write_text(
        "INPUT x\n"
        "LOAD_NAME 'print'\n"
        "PUSH_NULL\n"
        "LOAD_NAME 'x'\n"
        "CALL 1\n"
        "POP_TOP\n"
    )

    # Assemble to code
    code = assemble_file(src)

    # Monkeypatch builtins.input to return "42"
    import builtins
    monkeypatch.setattr(builtins, "input", lambda: "42")

    # Execute as module and check side effect
    g = {"__name__": "__main__"}
    exec(code, g)
    assert g.get("x") == "42"


@pytest.mark.parametrize("program, msg_fragment", [
    ("INPUT\n", "expects an identifier"),
    ("INPUT 123\n", "expects an identifier"),
])
def test_input_errors_missing_or_non_identifier(tmp_path: Path, program: str, msg_fragment: str):
    src = tmp_path / "bad.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert msg_fragment in str(exc.value)


def test_input_error_extra_token(tmp_path: Path):
    src = tmp_path / "bad2.paxy"
    src.write_text("INPUT x 1\n")
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    # generic extra-arg error from the common path is fine
    assert "extra argument" in str(exc.value)
