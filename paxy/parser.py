# paxy/parser.py
from __future__ import annotations

from typing import Any, Callable, List, Union
from pathlib import Path
from tokenize import tokenize, TokenInfo
from token import tok_name
from bytecode import Instr
import ast
import dis
import re

from paxy.constants import COND_JUMP_OPS, UNCOND_JUMP_FIXED
from .ident import Ident
from paxy.basic import is_basic_op, basic_op
from paxy.labels import NamedJump, LabelDecl, JumpRef
from paxy.opcoerce import (
    coerce_binary_op,
    coerce_compare_op,
    coerce_contains_op,
    coerce_is_op,
)

VALID_OPS = set(dis.opmap)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

ParsedItem = Union[Instr, NamedJump, LabelDecl, JumpRef]


class Parser:
    _NATIVE_COERCERS: dict[str, Callable[[Any], Any]] = {
        "BINARY_OP": coerce_binary_op,
        "COMPARE_OP": coerce_compare_op,  # EQ/NE/LT/LE/GT/GE in 3.13
        "IS_OP": coerce_is_op,  # 0 -> IS, 1 -> IS_NOT
        "CONTAINS_OP": coerce_contains_op,  # 0 -> IN, 1 -> NOT_IN
    }

    def __init__(self) -> None:
        self.encoding = "utf-8"
        self.current_op: str | None = None
        self.current_args: list[object] = []
        self.current_op_lineno: int | None = None
        self.pending_sign: int = 1
        self.instructions: list[ParsedItem] = []

        self.handlers: dict[str, Callable[[TokenInfo], None]] = {
            "ENCODING": self.handle_encoding,
            "NAME": self.handle_name,
            "STRING": self.handle_string,
            "NUMBER": self.handle_number,
            "OP": self.handle_op,  # unary '-'
            "NEWLINE": self.handle_newline,
            "NL": self.handle_nl,
            "COMMENT": self.handle_comment,
            "ENDMARKER": self.handle_endmarker,
        }

    def parse_file(self, src_path: Path) -> list[ParsedItem]:
        self._reset_state()
        self._process_stream(src_path)
        self._finalize_lines()
        self._ensure_framing()
        return self.instructions

    # ---- tokens ----

    def process_token(self, tok_info: TokenInfo) -> None:
        token_type_name: str | None = tok_name.get(tok_info.type)
        if token_type_name is None:
            return
        handler = self.handlers.get(token_type_name)
        if handler is not None:
            handler(tok_info)

    def handle_encoding(self, tok_info: TokenInfo) -> None:
        self.encoding = tok_info.string

    def handle_name(self, tok_info: TokenInfo) -> None:
        s = tok_info.string
        if self.current_op is None:
            op = s.upper()
            if self._is_opcode_name(op):
                self.current_op = op
                self.current_op_lineno = tok_info.start[0]
                return
            raise SyntaxError(f"Unknown opcode '{s}' at line {tok_info.start[0]}")

        if self._is_literal_name(s):
            self.current_args.append(self._literal_value(s))
        else:
            self.current_args.append(Ident(s))

    def handle_string(self, tok_info: TokenInfo) -> None:
        try:
            val = ast.literal_eval(tok_info.string)
        except Exception:
            val = tok_info.string
        self.current_args.append(val)

    def handle_number(self, tok_info: TokenInfo) -> None:
        val = self._parse_number(tok_info.string, self.pending_sign)
        self.pending_sign = 1
        self.current_args.append(val)

    def handle_op(self, tok_info: TokenInfo) -> None:
        if tok_info.string == "-" and self.current_op is not None:
            self.pending_sign = -1

    def handle_nl(self, tok_info: TokenInfo) -> None:
        pass

    def handle_comment(self, tok_info: TokenInfo) -> None:
        pass

    def handle_newline(self, tok_info: TokenInfo) -> None:
        if self.current_op is not None:
            self.store_instruction()

    def handle_endmarker(self, tok_info: TokenInfo) -> None:
        if self.current_op is not None:
            self.store_instruction()

    # ---- emit ----

    def store_instruction(self) -> None:
        op = self.current_op
        args = self.current_args
        lineno = self.current_op_lineno or 1

        self.current_op = None
        self.current_args = []
        self.current_op_lineno = None
        self.pending_sign = 1

        if op is None:
            return

        if is_basic_op(op):
            lowered = basic_op(op, args, lineno)  # list[Instr|LabelDecl|JumpRef]
            self.instructions.extend(lowered)
            return

        if len(args) == 0:
            self.instructions.append(Instr(op, lineno=lineno))
            return

        if len(args) == 1:
            coerced: Any = self._coerce_native_arg(op, args[0])
            self._emit_jump_or_instr(op, coerced, lineno)
            return

        raise SyntaxError(f"{op} takes at most one argument (got {len(args)})")

    # ---- framing / state ----

    def _reset_state(self) -> None:
        self.encoding = "utf-8"
        self.current_op = None
        self.current_args = []
        self.current_op_lineno = None
        self.pending_sign = 1
        self.instructions.clear()

    def _process_stream(self, src_path: Path) -> None:
        with src_path.open("rb") as f:
            for tok_info in tokenize(f.readline):
                self.process_token(tok_info)

    def _finalize_lines(self) -> None:
        if self.current_op is not None:
            self.store_instruction()

    def _ensure_framing(self) -> None:
        """Idempotently ensure RESUME at start and RETURN_* at end."""
        instrs = self.instructions
        if not instrs:
            instrs.extend(
                [Instr("RESUME", 0, lineno=1), Instr("RETURN_CONST", 0, lineno=1)]
            )
            return

        def _iname(x: ParsedItem) -> str:
            # Only real Instrs carry an opcode name; placeholders don't matter here.
            return str(x.name) if isinstance(x, Instr) else ""

        if _iname(instrs[0]) != "RESUME":
            ln = getattr(instrs[0], "lineno", 1) or 1
            instrs.insert(0, Instr("RESUME", 0, lineno=ln))

        if _iname(instrs[-1]) not in {"RETURN_CONST", "RETURN_VALUE"}:
            ln = getattr(instrs[-1], "lineno", 1) or 1
            instrs.append(Instr("RETURN_CONST", 0, lineno=ln))

    # ---- helpers ----

    def _is_opcode_name(self, upper: str) -> bool:
        return is_basic_op(upper) or upper in VALID_OPS

    def _is_literal_name(self, s: str) -> bool:
        return s in {"None", "True", "False"}

    def _literal_value(self, s: str) -> object:
        return {"None": None, "True": True, "False": False}[s]

    def _parse_number(self, text: str, sign: int) -> object:
        try:
            return sign * int(text, 0)
        except ValueError:
            pass
        try:
            return sign * float(text)
        except ValueError:
            pass
        return text if sign == 1 else f"-{text}"

    def _emit_basic(self, op: str, args: list[object], lineno: int) -> None:
        lowered = basic_op(op, args, lineno)
        self.instructions.extend(lowered)

    def _emit_jump_or_instr(self, op: str, arg0: Any, lineno: int) -> None:
        if op in COND_JUMP_OPS or op in UNCOND_JUMP_FIXED:
            if isinstance(arg0, (Ident, str)):
                # BEFORE: NamedJump(opcode=op, target=str(arg0), lineno=lineno)
                self.instructions.append(
                    NamedJump(opcode=op, target_name=str(arg0), lineno=lineno)
                )
                return
        self.instructions.append(Instr(op, arg0, lineno=lineno))

    def _coerce_native_arg(self, op: str, arg: Any) -> Any:
        fn = self._NATIVE_COERCERS.get(op.upper())
        return fn(arg) if fn else arg
