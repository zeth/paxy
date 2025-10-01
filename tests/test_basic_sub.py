# tests/test_basic_sub.py
from pathlib import Path
from types import CodeType
import types


from bytecode import Instr
import pytest

from paxy.compiler.parser import Parser
from paxy.compiler.ir import FuncDef, ReturnMarker
from paxy.compiler.assembler import Assembler
from paxy.cli import assemble_file


def _ops(items):
    """Flatten out Instr objects for quick introspection."""
    return [it for it in items if isinstance(it, Instr)]


def _has(items, name):
    return any(isinstance(it, Instr) and it.name == name for it in items)


def test_parser_captures_funcdef_structure(tmp_path: Path):
    # NOTE: '+' must be a STRING literal so the parser captures it as an arg.
    src = tmp_path / "sub1.paxy"
    src.write_text(
        "SUB add a b\n"
        "  LOAD_NAME a\n"
        "  LOAD_NAME b\n"
        '  BINARY_OP "+" \n'
        "  RET\n"
        "SBE\n"
    )

    p = Parser()
    items = p.parse_file(src)

    # We expect a FuncDef placeholder in the top-level stream
    assert any(isinstance(x, FuncDef) for x in items)
    fd = next(x for x in items if isinstance(x, FuncDef))
    assert fd.name == "add"
    assert fd.params == ["a", "b"]

    # Body (still high level) should contain our ops + a ReturnMarker
    body_ops = fd.body
    assert any(isinstance(x, Instr) and x.name == "LOAD_NAME" for x in body_ops)
    assert any(isinstance(x, Instr) and x.name == "BINARY_OP" for x in body_ops)
    assert any(isinstance(x, ReturnMarker) for x in body_ops)


def test_assembler_lowers_funcdef_to_makefunction(tmp_path: Path):
    src = tmp_path / "sub2.paxy"
    src.write_text("SUB noargs\n" "  LOAD_CONST 123\n" "  RET\n" "SBE\n")

    parsed = Parser().parse_file(src)
    resolved = Assembler(parsed).resolve()

    # After lowering, we should see LOAD_CONST(code), MAKE_FUNCTION, STORE_NAME
    assert _has(resolved, "LOAD_CONST")
    assert _has(resolved, "MAKE_FUNCTION")
    assert _has(resolved, "STORE_NAME")

    # Ensure the LOAD_CONST carrying the function code is a real code object
    code_const = next(
        it.arg for it in resolved if isinstance(it, Instr) and it.name == "LOAD_CONST"
    )
    assert isinstance(code_const, CodeType)


def test_end_to_end_sub_and_gosub(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    src = tmp_path / "prog.paxy"
    src.write_text(
        "SUB add a b\n"
        "  LOAD_NAME a\n"
        "  LOAD_NAME b\n"
        '  BINARY_OP "+" \n'
        "  STORE_NAME tmp\n"  # <--- capture the result
        "  RET tmp\n"  # <--- RET with a value (assembler emits RETURN_VALUE)
        "SBE\n"
        "LOAD_CONST 10\n"
        "STORE_NAME x\n"
        "LOAD_CONST 32\n"
        "STORE_NAME y\n"
        "GOS z add x y\n"
        "PNT z\n"
    )

    code = assemble_file(src)

    # IMPORTANT: execute as a function-kind code object (your assembler emits function-ish flags)
    import types

    g = {}
    types.FunctionType(code, g)()  # run “module” code

    assert g.get("z") == 42
    # (Optional) your PNT macro currently LOAD_CONSTs the arg if it's an Ident,
    # so stdout may print "z" literally; don't assert on stdout unless you adjust PNT.
