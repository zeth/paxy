# paxy/parser.py
from __future__ import annotations

from typing import Any, Callable, List, Union, Optional, Dict
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


# ----------------------------- Small helpers -----------------------------


class LineState:
    """Holds the in-progress line (opcode + args) while scanning tokens."""

    def __init__(self) -> None:
        self.current_op: Optional[str] = None
        self.current_args: list[object] = []
        self.current_op_lineno: Optional[int] = None
        self.pending_sign: int = 1

    # lifecycle
    def reset(self) -> None:
        self.current_op = None
        self.current_args = []
        self.current_op_lineno = None
        self.pending_sign = 1

    # reading
    def has_op(self) -> bool:
        return self.current_op is not None

    def begin_op(self, op: str, lineno: int) -> None:
        self.current_op = op
        self.current_op_lineno = lineno

    def add_arg(self, value: object) -> None:
        self.current_args.append(value)

    def mark_unary_minus(self) -> None:
        self.pending_sign = -1

    # snapshot
    def snapshot(self) -> tuple[Optional[str], list[object], int]:
        lineno = self.current_op_lineno or 1
        return self.current_op, self.current_args, lineno


class Emitter:
    """Collects parsed items and enforces framing."""

    def __init__(self, sink: list[ParsedItem]) -> None:
        self.sink = sink

    def emit_basic(self, op: str, args: list[object], lineno: int) -> None:
        lowered = basic_op(op, args, lineno)  # list[Instr|LabelDecl|JumpRef]
        self.sink.extend(lowered)

    def emit_instr(self, op: str, arg: Any, lineno: int) -> None:
        self.sink.append(Instr(op, arg, lineno=lineno))

    def emit_noarg(self, op: str, lineno: int) -> None:
        self.sink.append(Instr(op, lineno=lineno))

    def emit_named_jump(self, opcode: str, target_name: str, lineno: int) -> None:
        self.sink.append(
            NamedJump(opcode=opcode, target_name=target_name, lineno=lineno)
        )

    def ensure_framing(self) -> None:
        """Idempotently ensure RESUME at start and RETURN_* at end."""
        instrs = self.sink
        if not instrs:
            instrs.extend(
                [Instr("RESUME", 0, lineno=1), Instr("RETURN_CONST", 0, lineno=1)]
            )
            return

        def _iname(x: ParsedItem) -> str:
            return str(x.name) if isinstance(x, Instr) else ""

        if _iname(instrs[0]) != "RESUME":
            ln = getattr(instrs[0], "lineno", 1) or 1
            instrs.insert(0, Instr("RESUME", 0, lineno=ln))

        if _iname(instrs[-1]) not in {"RETURN_CONST", "RETURN_VALUE"}:
            ln = getattr(instrs[-1], "lineno", 1) or 1
            instrs.append(Instr("RETURN_CONST", 0, lineno=ln))


# -------------------------------- Parser --------------------------------


class Parser:
    _NATIVE_COERCERS: dict[str, Callable[[Any], Any]] = {
        "BINARY_OP": coerce_binary_op,
        "COMPARE_OP": coerce_compare_op,  # EQ/NE/LT/LE/GT/GE in 3.13
        "IS_OP": coerce_is_op,  # 0 -> IS, 1 -> IS_NOT
        "CONTAINS_OP": coerce_contains_op,  # 0 -> IN, 1 -> NOT_IN
    }

    def __init__(self) -> None:
        self.encoding = "utf-8"
        self._line = LineState()
        self.instructions: list[ParsedItem] = []
        self._emit = Emitter(self.instructions)

        self.handlers: Dict[str, Callable[[TokenInfo], None]] = {
            "ENCODING": self._on_encoding,
            "NAME": self._on_name,
            "STRING": self._on_string,
            "NUMBER": self._on_number,
            "OP": self._on_op,  # unary '-'
            "NEWLINE": self._on_newline,
            "NL": self._on_nl,
            "COMMENT": self._on_comment,
            "ENDMARKER": self._on_endmarker,
        }

    # ---- public API ----

    def parse_file(self, src_path: Path) -> list[ParsedItem]:
        self._reset_state()
        self._process_stream(src_path)
        self._flush_pending_line()  # if file lacked trailing newline
        self._emit.ensure_framing()
        return self.instructions

    # ---- stream driver ----

    def process_token(self, tok_info: TokenInfo) -> None:
        token_type_name: Optional[str] = tok_name.get(tok_info.type)
        if token_type_name is None:
            return
        handler = self.handlers.get(token_type_name)
        if handler:
            handler(tok_info)

    def _process_stream(self, src_path: Path) -> None:
        with src_path.open("rb") as f:
            for tok_info in tokenize(f.readline):
                self.process_token(tok_info)

    # ---- token handlers ----

    def _on_encoding(self, tok_info: TokenInfo) -> None:
        self.encoding = tok_info.string

    def _on_name(self, tok_info: TokenInfo) -> None:
        s = tok_info.string
        if not self._line.has_op():
            op = s.upper()
            if self._is_opcode_name(op):
                self._line.begin_op(op, tok_info.start[0])
                return
            raise SyntaxError(f"Unknown opcode '{s}' at line {tok_info.start[0]}")

        if self._is_literal_name(s):
            self._line.add_arg(self._literal_value(s))
        else:
            self._line.add_arg(Ident(s))

    def _on_string(self, tok_info: TokenInfo) -> None:
        try:
            val = ast.literal_eval(tok_info.string)
        except Exception:
            val = tok_info.string
        self._line.add_arg(val)

    def _on_number(self, tok_info: TokenInfo) -> None:
        val = self._parse_number(tok_info.string, self._line.pending_sign)
        self._line.pending_sign = 1
        self._line.add_arg(val)

    def _on_op(self, tok_info: TokenInfo) -> None:
        if tok_info.string == "-" and self._line.has_op():
            self._line.mark_unary_minus()

    def _on_nl(self, tok_info: TokenInfo) -> None:  # noqa: ARG002
        pass

    def _on_comment(self, tok_info: TokenInfo) -> None:  # noqa: ARG002
        pass

    def _on_newline(self, tok_info: TokenInfo) -> None:  # noqa: ARG002
        self._flush_line_if_any()

    def _on_endmarker(self, tok_info: TokenInfo) -> None:  # noqa: ARG002
        self._flush_line_if_any()

    # ---- line flushing / emission ----

    def _flush_line_if_any(self) -> None:
        if self._line.has_op():
            self._store_instruction_from_line()

    def _flush_pending_line(self) -> None:
        # called once after tokenization completes
        self._flush_line_if_any()

    def _store_instruction_from_line(self) -> None:
        op, args, lineno = self._line.snapshot()
        self._line.reset()
        if op is None:
            return

        # BASIC macro lines
        if is_basic_op(op):
            self._emit.emit_basic(op, args, lineno)
            return

        # Native opcode lines
        if not args:
            self._emit.emit_noarg(op, lineno)
            return

        if len(args) == 1:
            coerced: Any = self._coerce_native_arg(op, args[0])
            self._emit_jump_or_instr(op, coerced, lineno)
            return

        raise SyntaxError(f"{op} takes at most one argument (got {len(args)})")

    # ---- helpers: classification & literals ----

    def _is_opcode_name(self, upper: str) -> bool:
        return is_basic_op(upper) or upper in VALID_OPS

    def _is_literal_name(self, s: str) -> bool:
        return s in {"None", "True", "False"}

    def _literal_value(self, s: str) -> object:
        return {"None": None, "True": True, "False": False}[s]

    # ---- helpers: numbers & unary minus ----

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

    # ---- helpers: native emission ----

    def _emit_jump_or_instr(self, op: str, arg0: Any, lineno: int) -> None:
        if op in COND_JUMP_OPS or op in UNCOND_JUMP_FIXED:
            if isinstance(arg0, (Ident, str)):
                self._emit.emit_named_jump(
                    opcode=op, target_name=str(arg0), lineno=lineno
                )
                return
        self._emit.emit_instr(op, arg0, lineno)

    def _coerce_native_arg(self, op: str, arg: Any) -> Any:
        fn = self._NATIVE_COERCERS.get(op.upper())
        return fn(arg) if fn else arg

    # ---- reset ----

    def _reset_state(self) -> None:
        self.encoding = "utf-8"
        self._line.reset()
        self.instructions.clear()
