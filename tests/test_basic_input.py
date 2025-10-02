from pathlib import Path
import pytest

from paxy.compiler.parser import Parser
from paxy.cli import assemble_file


def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]


def strip_leading_resume(pairs):
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    return out


def norm_argless(pairs):
    out = []
    for n, a in pairs:
        if n in {"PUSH_NULL", "POP_TOP", "RETURN_VALUE"}:
            out.append((n, 0))  # canonicalize arg-less to 0
        else:
            out.append((n, a))
    return out


def test_input_lowers_to_call_and_store(tmp_path: Path):
    src = tmp_path / "inp.paxy"
    src.write_text("INP x\nLOAD_CONST None\nRETURN_VALUE\n")

    got = norm_argless(strip_leading_resume(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "input"),
        ("PUSH_NULL", 0),
        ("CALL", 0),
        ("STORE_NAME", "x"),
        ("LOAD_CONST", None),
        ("RETURN_VALUE", 0),
    ]


def test_input_runtime_reads_and_stores_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Program: read into x, then print x to prove value is there
    src = tmp_path / "inp2.paxy"
    src.write_text(
        "INP x\n"
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


@pytest.mark.parametrize(
    "program, expected_msg",
    [
        ("INP\n", "takes exactly one identifier"),
        ("INP 123\n", "expects an identifier"),
    ],
)
def test_input_errors_missing_or_non_identifier(
    tmp_path: Path, program: str, expected_msg: str
):
    src = tmp_path / "bad.paxy"
    src.write_text(program)
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert expected_msg in str(exc.value)


def test_input_error_extra_token(tmp_path: Path):
    src = tmp_path / "bad2.paxy"
    src.write_text("INP x 1\n")
    with pytest.raises(SyntaxError) as exc:
        Parser().parse_file(src)
    assert "takes exactly one identifier" in str(exc.value)
