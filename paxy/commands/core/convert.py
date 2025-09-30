from __future__ import annotations
from typing import Any

from bytecode import Instr  # type: ignore[import-untyped]
from paxy.commands.base import Command
from paxy.compiler.ir import Ident

__all__ = ["ToInt", "ToFloat", "ToStr"]


class _ConvertBase(Command):
    CATEGORY = "core"

    def _emit_load_token(self, tok: Any) -> None:
        if isinstance(tok, Ident):
            # Module-level will be LOAD_NAME; your function rewriter will turn
            # these into LOAD_FAST inside SUB bodies.
            self.add_op("LOAD_NAME", str(tok))
        else:
            self.add_op("LOAD_CONST", tok)

    def _emit_store_name(self, ident: Ident) -> None:
        self.add_op("STORE_NAME", str(ident))


class ToInt(_ConvertBase):
    COMMAND = "TOINT"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2 or not isinstance(args[0], Ident):
            raise SyntaxError("TOINT: usage: TOINT <dst> <src>")
        dst, src = args  # type: ignore[misc]
        self.add_op("LOAD_GLOBAL", (True, "int"))
        self._emit_load_token(src)
        self.add_op("CALL", 1)
        self._emit_store_name(dst)


class ToFloat(_ConvertBase):
    COMMAND = "TOFLOAT"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2 or not isinstance(args[0], Ident):
            raise SyntaxError("TOFLOAT: usage: TOFLOAT <dst> <src>")
        dst, src = args  # type: ignore[misc]
        self.add_op("LOAD_GLOBAL", (True, "float"))
        self._emit_load_token(src)
        self.add_op("CALL", 1)
        self._emit_store_name(dst)


class ToStr(_ConvertBase):
    COMMAND = "TOSTR"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2 or not isinstance(args[0], Ident):
            raise SyntaxError("TOSTR: usage: TOSTR <dst> <src>")
        dst, src = args  # type: ignore[misc]
        self.add_op("LOAD_GLOBAL", (True, "str"))
        self._emit_load_token(src)
        self.add_op("CALL", 1)
        self._emit_store_name(dst)
