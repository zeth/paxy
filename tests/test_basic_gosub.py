# tests/test_basic_gosub.py
from bytecode import Instr
import pytest

from paxy.commands.core.gosub import Gosub
from paxy.compiler.ir import Ident


def ops_of(op):
    seq = []
    for ins in getattr(op, "ops"):
        assert isinstance(ins, Instr)
        seq.append((ins.name, getattr(ins, "arg", None)))
    return seq


def test_gosub_no_args_uses_load_global_push_null_call_then_store():
    g = Gosub([Ident("z"), Ident("foo")], lineno=1)
    assert ops_of(g) == [
        ("LOAD_GLOBAL", (True, "foo")),  # auto-push NULL under callable
        ("CALL", 0),
        ("STORE_NAME", "z"),
    ]


def test_gosub_with_ident_and_literal_args():
    g = Gosub([Ident("out"), Ident("add"), Ident("x"), 5], lineno=10)
    assert ops_of(g) == [
        ("LOAD_GLOBAL", (True, "add")),
        ("LOAD_NAME", "x"),
        ("LOAD_CONST", 5),
        ("CALL", 2),
        ("STORE_NAME", "out"),
    ]


def test_gosub_accepts_string_function_name():
    g = Gosub([Ident("res"), "doit", 1, 2, 3], lineno=3)
    assert ops_of(g) == [
        ("LOAD_GLOBAL", (True, "doit")),
        ("LOAD_CONST", 1),
        ("LOAD_CONST", 2),
        ("LOAD_CONST", 3),
        ("CALL", 3),
        ("STORE_NAME", "res"),
    ]


def test_gosub_requires_dest_identifier():
    with pytest.raises(SyntaxError):
        Gosub(["not_ident", Ident("fn")], lineno=1)


def test_gosub_requires_function_name_token():
    with pytest.raises(SyntaxError):
        Gosub([Ident("dst"), 123], lineno=1)


def test_gosub_arity_errors_message_is_helpful():
    with pytest.raises(SyntaxError) as ex:
        Gosub([Ident("dst")], lineno=1)
    assert "GOS expects" in str(ex.value)
