# paxy/parser.py

from typing import Any, Callable, Optional, Dict, Iterable, Iterator
from pathlib import Path
from tokenize import tokenize, TokenInfo
from token import tok_name
from bytecode import Instr
import ast
import re

from paxy.commands import is_command, command, is_command_name
from paxy.compiler.opcoerce import (
    coerce_binary_op,
    coerce_compare_op,
    coerce_contains_op,
    coerce_is_op,
)
from paxy.compiler.ir import (
    NamedJump,
    FuncDef,
    Ident,
    ParsedItem,
    RangeBlock,
    COND_JUMP_OPS,
    UNCOND_JUMP_FIXED,
)

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Operators allowed bare (without quotes) inside instruction arguments
_ALLOWED_OPS = {
    "+",
    "-",
    "*",
    "/",
    "%",
    "//",
    "**",
    "==",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "|",
    "&",
    "^",
    "<<",
    ">>",
}

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
        lowered = command(op, args, lineno)  # list[Instr|LabelDecl|JumpRef|...]
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
                [
                    Instr("RESUME", 0, lineno=1),
                    Instr("LOAD_CONST", 0, lineno=1),
                    Instr("RETURN_VALUE", lineno=1),
                ]
            )
            return

        def _iname(x: ParsedItem) -> str:
            return str(x.name) if isinstance(x, Instr) else ""

        if _iname(instrs[0]) != "RESUME":
            ln = getattr(instrs[0], "lineno", 1) or 1
            instrs.insert(0, Instr("RESUME", 0, lineno=ln))

        if _iname(instrs[-1]) != "RETURN_VALUE":
            ln = getattr(instrs[-1], "lineno", 1) or 1
            instrs.extend(
                [
                    Instr("LOAD_CONST", 0, lineno=ln),
                    Instr("RETURN_VALUE", lineno=ln),
                ]
            )


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

        # Token iterator (needed to capture SUB bodies)
        self._tok_iter: Iterator[TokenInfo] | None = None

    # ---- public API ----

    def parse_file(self, src_path: Path) -> list[ParsedItem]:
        self._reset_state()
        with src_path.open("rb") as f:
            self._parse_token_iter(tokenize(f.readline))
        self._flush_pending_line()  # if file lacked trailing newline
        self._emit.ensure_framing()
        return self.instructions

    def parse_tokens(self, toks: Iterable[TokenInfo]) -> list[ParsedItem]:
        """Parse from an existing token stream (used for SUB bodies)."""
        self._reset_state()
        self._parse_token_iter(toks)
        self._flush_pending_line()
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

    def _parse_token_iter(
        self, tok_iter: Iterable[TokenInfo] | Iterator[TokenInfo]
    ) -> None:
        it = iter(tok_iter)
        self._tok_iter = it
        for tok_info in it:
            self.process_token(tok_info)

    # ---- token handlers ----

    def _on_encoding(self, tok_info: TokenInfo) -> None:
        self.encoding = tok_info.string

    def _on_name(self, tok_info: TokenInfo) -> None:
        s = tok_info.string
        if not self._line.has_op():
            op = s.upper()
            if is_command_name(op):
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
        op = tok_info.string
        if op == "-" and self._line.has_op():
            # Handle unary minus (applies to the *next* number token)
            self._line.mark_unary_minus()
            return

        # If we’re inside an instruction, and the op is allowed, treat it as an arg
        if self._line.has_op() and op in _ALLOWED_OPS:
            self._line.add_arg(op)
            return

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

        # RNG block
        if op == "RNG":
            self._handle_range_block(args, lineno)
            return

        # Special-case: SUB … SBE
        if op == "SUB":
            self._handle_sub_definition(args, lineno)
            return

        # BASIC macro lines
        if is_command(op):
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

    # ---- RNG support ----

    def _handle_range_block(self, args: list[object], lineno: int) -> None:
        # Expect: RNG <ident> <start> <end>
        if len(args) != 3 or not isinstance(args[0], Ident):
            raise SyntaxError("RNG expects: RNG <var> <start> <end>")
        var_ident = args[0]
        start_tok = args[1]
        end_tok = args[2]

        # Collect tokens until RNE (reuse your existing collector for SUB)
        body_tokens = self._collect_tokens_until("RNE")
        inner = Parser()  # nested parser for the block
        body_items = inner.parse_tokens(body_tokens)

        self.instructions.append(
            RangeBlock(
                var=str(var_ident),
                start=start_tok,
                end=end_tok,
                body=body_items,
                lineno=lineno,
            )
        )

    # ---- SUB support ----

    def _handle_sub_definition(self, args: list[object], lineno: int) -> None:
        """
        SUB <name> [params...] ... SBE
        Capture tokens until a line that *starts* with NAME 'SBE' and parse them
        with a fresh Parser to produce the function body.
        """
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("SUB expects: SUB <name> [params...]")
        name = str(args[0])

        params: list[str] = []
        for a in args[1:]:
            if not isinstance(a, Ident):
                raise SyntaxError("SUB parameters must be identifiers")
            params.append(str(a))

        body_tokens = self._collect_tokens_until("SBE")
        inner = Parser()
        body_items = inner.parse_tokens(body_tokens)

        self.instructions.append(
            FuncDef(name=name, params=params, body=body_items, lineno=lineno)
        )

    def _collect_tokens_until(self, end_op: str) -> list[TokenInfo]:
        """
        Consume tokens from self._tok_iter and collect all tokens belonging to the
        current block until we see a line whose first NAME token matches `end_op`
        (e.g. 'SBE' or 'RNE'). The terminator line itself is consumed
        (up to its NEWLINE) but not included. Supports nesting for matching pairs:
        SUB ... SBE
        RNG ... RNE
        """
        if self._tok_iter is None:
            raise RuntimeError("internal: token iterator missing")
        it: Iterator[TokenInfo] = self._tok_iter  # narrow for type checker

        # For simple same-kind nesting: which opener corresponds to this closer?
        opener_for: dict[str, str] = {"SBE": "SUB", "RNE": "RNG"}
        opener = opener_for.get(end_op, None)

        collected: list[TokenInfo] = []
        pending_op: Optional[str] = None
        depth = 0  # nesting depth for same-kind blocks

        def _consume_to_eol() -> None:
            for t2 in it:
                t2name = tok_name.get(t2.type)
                if t2name in {"NEWLINE", "ENDMARKER"}:
                    break

        for tok in it:
            tname = tok_name.get(tok.type)

            # Detect the first NAME at the start of a logical line
            if tname == "NAME" and pending_op is None:
                candidate = tok.string.upper()

                # opener? -> increase nesting and keep the line
                if opener and candidate == opener:
                    depth += 1
                    pending_op = candidate
                    collected.append(tok)
                    continue

                # closer? -> if at top level, consume that line and stop;
                #            if nested, consume that line and reduce depth, keep collecting
                if candidate == end_op:
                    _consume_to_eol()
                    if depth == 0:
                        break
                    depth -= 1
                    # do not include the closer line in the body
                    pending_op = None
                    continue

                # ordinary line with some opcode/name
                pending_op = candidate

            collected.append(tok)

            if tname in {"NEWLINE", "ENDMARKER"}:
                pending_op = None
                if tname == "ENDMARKER":
                    break

        return collected

    # ---- helpers: classification & literals ----

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
        self._tok_iter = None
