from pathlib import Path
from tokenize import tokenize, TokenInfo
from token import tok_name
from bytecode import Instr
import ast
import dis

VALID_OPS = set(dis.opmap)  # CPython 3.13 opcode names

class ExplicitNone:
    """Sentinel to mean the literal word 'None' in source, as an argument."""
    pass

class Parser:
    def __init__(self):
        self.encoding = "utf-8"
        self.current_arg = None
        self.current_op = None
        self.current_op_lineno = None
        self.pending_sign = 1     # handles unary minus for numbers
        self.instructions = []

        # Map token names to handlers
        self.handlers = {
            "ENCODING": self.handle_encoding,
            "NAME": self.handle_name,
            "STRING": self.handle_string,
            "NUMBER": self.handle_number,
            "OP": self.handle_op,           # for unary '-' before NUMBER
            "NEWLINE": self.handle_newline,
            "NL": self.handle_nl,           # ignore soft newlines
            "COMMENT": self.handle_comment, # tokenizer gives this only for '#'
            "ENDMARKER": self.handle_endmarker,
        }

    def parse_file(self, src_path: Path):
        # reset state
        self.instructions.clear()
        self.current_op = None
        self.current_arg = None
        self.current_op_lineno = None
        self.pending_sign = 1

        with src_path.open("rb") as f:
            for tok_info in tokenize(f.readline):
                self.process_token(tok_info)
        return self.instructions

    def process_token(self, tok_info: TokenInfo):
        token_type_name = tok_name.get(tok_info.type, None)
        handler = self.handlers.get(token_type_name)
        if handler is not None:
            handler(tok_info)
        # else: ignore token kinds we don’t care about

    # --- Handlers ---

    def handle_encoding(self, tok_info: TokenInfo):
        self.encoding = tok_info.string

    def handle_name(self, tok_info: TokenInfo):
        s = tok_info.string

        # Booleans and None as literal arguments
        if s == "None":
            return self.handle_none(tok_info)
        if s == "True":
            return self._set_arg(True)
        if s == "False":
            return self._set_arg(False)

        # Opcode at line start
        if self.current_op is None:
            op = s.upper()
            if op not in VALID_OPS:
                raise SyntaxError(f"Unknown opcode '{s}' at line {tok_info.start[0]}")
            self.current_op = op
            self.current_op_lineno = tok_info.start[0]
            return

        # If we ever decide NAME can be an arg, handle here.
        raise SyntaxError(
            f"Unexpected NAME '{s}' where an argument or newline was expected "
            f"(line {tok_info.start[0]})"
        )

    def handle_string(self, tok_info: TokenInfo):
        try:
            val = ast.literal_eval(tok_info.string)
        except Exception:
            val = tok_info.string
        self._set_arg(val)

    def handle_number(self, tok_info: TokenInfo):
        text = tok_info.string.replace("_", "_")  # allow underscores (int/float accept them)
        sign = self.pending_sign
        self.pending_sign = 1  # consume sign

        # Try int with auto base (0x, 0o, 0b supported)
        try:
            val = int(text, 0)
            self._set_arg(sign * val)
            return
        except ValueError:
            pass

        # Try float
        try:
            val = float(text)
            self._set_arg(sign * val)
            return
        except ValueError:
            pass

        # Fallback: keep raw string
        self._set_arg(text if sign == 1 else f"-{text}")

    def handle_op(self, tok_info: TokenInfo):
        # Only unary minus supported for numbers: e.g. "LOAD_CONST -5"
        if tok_info.string == "-" and self.current_op is not None and self.current_arg is None:
            self.pending_sign = -1
            return
        # Ignore other operators silently; we can tighten this later.
        # If you want to forbid them:
        # raise SyntaxError(f"Unexpected operator '{tok_info.string}' at line {tok_info.start[0]}")

    def handle_nl(self, tok_info: TokenInfo):
        pass  # soft newline inside logical line

    def handle_comment(self, tok_info: TokenInfo):
        pass  # tokenizer only marks '#' comments; ';' is not recognized here

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
        if self.current_arg is not None:
            raise SyntaxError(f"Unexpected extra argument on line {self.current_op_lineno}")
        self.current_arg = value

    def store_instruction(self):
        op = self.current_op
        arg = self.current_arg
        lineno = self.current_op_lineno

        # reset for next line
        self.current_op = None
        self.current_arg = None
        self.current_op_lineno = None
        self.pending_sign = 1

        if op is None:
            return

        if isinstance(arg, ExplicitNone):
            instr = Instr(op, None)
        elif arg is not None:
            instr = Instr(op, arg)
        else:
            instr = Instr(op)

        # attach source line number for nicer diagnostics later
        instr.lineno = lineno
        self.instructions.append(instr)

if __name__ == "__main__":
    path = Path("examples/printer.paxy")
    parser = Parser()
    instrs = parser.parse_file(path)
    print(instrs)
