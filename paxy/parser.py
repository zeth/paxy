# paxy/parser.py
from __future__ import annotations
from pathlib import Path
from tokenize import tokenize, TokenInfo
from token import tok_name
from bytecode import Instr, BinaryOp
import ast
import dis
import re

from paxy.constants import COND_JUMP_OPS, UNCOND_JUMP_FIXED
from .ident import Ident
from paxy.basic import is_basic_op, basic_op
from paxy.labels import NamedJump


VALID_OPS = set(dis.opmap)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

BINARY_SYMBOL_MAP = {
    "+": "ADD",
    "-": "SUBTRACT",
    "*": "MULTIPLY",
    "/": "TRUE_DIVIDE",
    "//": "FLOOR_DIVIDE",
    "%": "MODULO",
    "**": "POWER",
    "<<": "LSHIFT",
    ">>": "RSHIFT",
    "|": "OR",
    "&": "AND",
    "^": "XOR",
    "@": "MATRIX_MULTIPLY",
}


class Parser:
    def __init__(self):
        self.encoding = "utf-8"
        self.current_op: str | None = None
        self.current_args: list[object] = []
        self.current_op_lineno: int | None = None
        self.pending_sign: int = 1
        self.instructions: list[Instr] = []

        self.handlers = {
            "ENCODING": self.handle_encoding,
            "NAME": self.handle_name,
            "STRING": self.handle_string,
            "NUMBER": self.handle_number,
            "OP": self.handle_op,            # unary '-'
            "NEWLINE": self.handle_newline,
            "NL": self.handle_nl,
            "COMMENT": self.handle_comment,
            "ENDMARKER": self.handle_endmarker,
        }

    def parse_file(self, src_path: Path):
        # reset state
        self.instructions.clear()
        self.current_op = None
        self.current_args = []
        self.current_op_lineno = None
        self.pending_sign = 1

        with src_path.open("rb") as f:
            for tok_info in tokenize(f.readline):
                self.process_token(tok_info)

        # if file didn’t end with a newline, flush any pending line
        if self.current_op is not None:
            self.store_instruction()

        # one-shot framing
        self.check_start()
        self.check_end()
        return self.instructions

    # ---- framing ----

    def _iname(self, ins: Instr) -> str:
        return str(ins.name)

    def check_start(self) -> None:
        instrs = self.instructions
        if not instrs:
            instrs.append(Instr("RESUME", 0, lineno=1))
            return
        if self._iname(instrs[0]) != "RESUME":
            ln = getattr(instrs[0], "lineno", 1) or 1
            instrs.insert(0, Instr("RESUME", 0, lineno=ln))

    def check_end(self) -> None:
        instrs = self.instructions
        if not instrs:
            instrs.extend([Instr("RESUME", 0, lineno=1), Instr("RETURN_CONST", None, lineno=1)])
            return
        if self._iname(instrs[-1]) not in {"RETURN_CONST", "RETURN_VALUE"}:
            ln = getattr(instrs[-1], "lineno", 1) or 1
            instrs.append(Instr("RETURN_CONST", None, lineno=ln))

    # ---- token handlers ----

    def process_token(self, tok_info: TokenInfo):
        token_type_name = tok_name.get(tok_info.type, None)
        handler = self.handlers.get(token_type_name)
        if handler is not None:
            handler(tok_info)

    def handle_encoding(self, tok_info: TokenInfo):
        self.encoding = tok_info.string

    def handle_name(self, tok_info: TokenInfo):
        s = tok_info.string

        # first NAME on a line = opcode
        if self.current_op is None:
            op = s.upper()
            if is_basic_op(op) or op in VALID_OPS:
                self.current_op = op
                self.current_op_lineno = tok_info.start[0]
                return
            raise SyntaxError(f"Unknown opcode '{s}' at line {tok_info.start[0]}")

        # after opcode: NAME tokens are identifiers, except these literals:
        if s == "None":
            self.current_args.append(None)
            return
        if s == "True":
            self.current_args.append(True)
            return
        if s == "False":
            self.current_args.append(False)
            return

        # identifier string (store raw; BASIC/native will validate if needed)
        self.current_args.append(Ident(s))

    def handle_string(self, tok_info: TokenInfo):
        try:
            val = ast.literal_eval(tok_info.string)
        except Exception:
            val = tok_info.string
        self.current_args.append(val)

    def handle_number(self, tok_info: TokenInfo):
        text = tok_info.string
        sign = self.pending_sign
        self.pending_sign = 1
        # int with auto base
        try:
            val = int(text, 0)
            self.current_args.append(sign * val)
            return
        except ValueError:
            pass
        # float
        try:
            val = float(text)
            self.current_args.append(sign * val)
            return
        except ValueError:
            pass
        # fallback (string)
        self.current_args.append(text if sign == 1 else f"-{text}")

    def handle_op(self, tok_info: TokenInfo):
        # Only unary minus folding: “- 5” → -5 for next NUMBER
        if tok_info.string == "-" and self.current_op is not None:
            # Only apply if next token is NUMBER; harmless if not
            self.pending_sign = -1

    def handle_nl(self, tok_info: TokenInfo):
        pass

    def handle_comment(self, tok_info: TokenInfo):
        pass

    def handle_newline(self, tok_info: TokenInfo):
        if self.current_op is not None:
            self.store_instruction()

    def handle_endmarker(self, tok_info: TokenInfo):
        if self.current_op is not None:
            self.store_instruction()

    def _coerce_native_arg(self, op: str, arg):
        """Normalize native-op arguments to the shapes bytecode expects."""
        if op == "BINARY_OP":
            # Accept symbol ('-'), enum name ('SUBTRACT'), or int code
            if isinstance(arg, str):
                name = BINARY_SYMBOL_MAP.get(arg, arg).upper()
                try:
                    return BinaryOp[name]
                except KeyError as e:
                    raise SyntaxError(f"Unknown BINARY_OP argument '{arg}'") from e
            if isinstance(arg, int):
                try:
                    return BinaryOp(arg)
                except Exception as e:
                    raise SyntaxError(f"Invalid BINARY_OP code {arg}") from e
        return arg

    # ---- emit ----

    def store_instruction(self):
        op = self.current_op
        args = self.current_args
        lineno = self.current_op_lineno or 1

        # reset for next line
        self.current_op = None
        self.current_args = []
        self.current_op_lineno = None
        self.pending_sign = 1

        if op is None:
            return

        # BASIC macro: pass the whole args list; validation lives in the handler
        if is_basic_op(op):
            lowered = basic_op(op, args, lineno)
            self.instructions.extend(lowered)
            return

        # native opcode
        if len(args) == 0:
            instr = Instr(op, lineno=lineno)
        elif len(args) == 1:
            # If this is a native jump that names a label, emit a placeholder
            if op in COND_JUMP_OPS or op in UNCOND_JUMP_FIXED:
                arg0 = args[0]
                if isinstance(arg0, (Ident, str)):
                    self.instructions.append(NamedJump(opcode=op, target=str(arg0), lineno=lineno))
                    return

            coerced = self._coerce_native_arg(op, args[0])
            instr = Instr(op, coerced, lineno=lineno)
        else:
            raise SyntaxError(f"{op} takes at most one argument (got {len(args)})")

        self.instructions.append(instr)
