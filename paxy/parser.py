# paxy/parser.py
from pathlib import Path
from tokenize import tokenize, TokenInfo
from token import tok_name
from bytecode import Instr
import ast
import dis
import re

from .basic import is_basic_op, basic_op

VALID_OPS = set(dis.opmap)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

class ExplicitNone:
    """Sentinel to mean the literal word 'None' in source, as an argument."""
    pass

class Parser:
    def __init__(self):
        self.encoding = "utf-8"
        self.current_arg = None
        self.current_op = None
        self.current_op_lineno = None
        self.pending_sign = 1
        self.instructions = []
        self.pending_let_name: str | None = None  # <- NEW

        self.handlers = {
            "ENCODING": self.handle_encoding,
            "NAME": self.handle_name,
            "STRING": self.handle_string,
            "NUMBER": self.handle_number,
            "OP": self.handle_op,
            "NEWLINE": self.handle_newline,
            "NL": self.handle_nl,
            "COMMENT": self.handle_comment,
            "ENDMARKER": self.handle_endmarker,
        }

    def parse_file(self, src_path: Path):
        # reset state
        self.instructions.clear()
        self.current_op = None
        self.current_arg = None
        self.current_op_lineno = None
        self.pending_sign = 1
        self.pending_let_name = None

        with src_path.open("rb") as f:
            for tok_info in tokenize(f.readline):
                self.process_token(tok_info)

        # if file lacks trailing newline
        if self.current_op is not None:
            self.store_instruction()

        # one-shot framing at the end
        self.check_start()
        self.check_end()
        return self.instructions

    # --- end framing ---

    def _iname(self, ins) -> str:
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

    # --- token handlers ---

    def process_token(self, tok_info: TokenInfo):
        token_type_name = tok_name.get(tok_info.type, None)
        handler = self.handlers.get(token_type_name)
        if handler is not None:
            handler(tok_info)

    def handle_encoding(self, tok_info: TokenInfo):
        self.encoding = tok_info.string

    def handle_name(self, tok_info: TokenInfo):
        s = tok_info.string

        # literals
        if s == "None":
            return self.handle_none(tok_info)
        if s == "True":
            return self._set_arg(True)
        if s == "False":
            return self._set_arg(False)

        # opcode at line start
        if self.current_op is None:
            op = s.upper()
            if is_basic_op(op):
                self.current_op = op
                self.current_op_lineno = tok_info.start[0]
                return
            if op not in VALID_OPS:
                raise SyntaxError(f"Unknown opcode '{s}' at line {tok_info.start[0]}")
            self.current_op = op
            self.current_op_lineno = tok_info.start[0]
            return

        # special case: LET expects an identifier name here
        if self.current_op == "LET" and self.pending_let_name is None:
            if not IDENT_RE.fullmatch(s):
                raise SyntaxError(f"LET expects an identifier, got '{s}' (line {tok_info.start[0]})")
            self.pending_let_name = s
            return

        # otherwise, NAME where a value should be is invalid (we only allow literals)
        raise SyntaxError(
            f"Unexpected NAME '{s}' where an argument or newline was expected (line {tok_info.start[0]})"
        )

    def handle_string(self, tok_info: TokenInfo):
        try:
            val = ast.literal_eval(tok_info.string)
        except Exception:
            val = tok_info.string
        self._set_arg(val)

    def handle_number(self, tok_info: TokenInfo):
        text = tok_info.string
        sign = self.pending_sign
        self.pending_sign = 1
        try:
            val = int(text, 0)
            return self._set_arg(sign * val)
        except ValueError:
            pass
        try:
            val = float(text)
            return self._set_arg(sign * val)
        except ValueError:
            pass
        self._set_arg(text if sign == 1 else f"-{text}")

    def handle_op(self, tok_info: TokenInfo):
        if tok_info.string == "-" and self.current_op is not None and self.current_arg is None:
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

    def handle_none(self, tok_info: TokenInfo):
        self._set_arg(ExplicitNone())

    # --- helpers ---

    def _set_arg(self, value):
        if self.current_op is None:
            raise SyntaxError("Argument encountered before opcode")

        # LET packs (name, value)
        if self.current_op == "LET":
            if self.pending_let_name is None:
                raise SyntaxError("LET expects an identifier before the value")
            if self.current_arg is not None:
                raise SyntaxError("LET takes exactly two arguments: name and literal")
            self.current_arg = (self.pending_let_name, None if isinstance(value, ExplicitNone) else value)
            return

        # non-LET: single argument max
        if self.current_arg is not None:
            raise SyntaxError(f"Unexpected extra argument on line {self.current_op_lineno}")
        self.current_arg = None if isinstance(value, ExplicitNone) else value

    def store_instruction(self):
        op = self.current_op
        arg = self.current_arg
        lineno = self.current_op_lineno

        # reset state for next line
        self.current_op = None
        self.current_arg = None
        self.current_op_lineno = None
        self.pending_sign = 1
        self.pending_let_name = None

        if op is None:
            return

        # BASIC macro lowering
        if is_basic_op(op):
            # Special-case: LET must have exactly two parts (name + value)
            if op == "LET":
                if not (isinstance(arg, tuple) and len(arg) == 2 and isinstance(arg[0], str)):
                    raise SyntaxError("LET takes exactly two arguments: name and literal")
            lowered = basic_op(op, arg, lineno)
            self.instructions.extend(lowered)
            return

        # native opcode
        if isinstance(arg, ExplicitNone):
            instr = Instr(op, None, lineno=lineno)
        elif arg is not None:
            instr = Instr(op, arg, lineno=lineno)
        else:
            instr = Instr(op, lineno=lineno)

        self.instructions.append(instr)
