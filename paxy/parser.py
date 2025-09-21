from pathlib import Path
from tokenize import tokenize, TokenInfo
from token import tok_name
from bytecode import Instr
import ast

class ExplicitNone:
    """Sentinel to mean the literal word 'None' in source, as an argument."""
    pass

class Parser:
    def __init__(self):
        self.encoding = "utf-8"
        self.current_arg = None
        self.current_op = None
        self.instructions = []

        # Add NL/COMMENT to ignore cleanly; map token names to handlers
        self.handlers = {
            "ENCODING": self.handle_encoding,
            "NAME": self.handle_name,
            "STRING": self.handle_string,
            "NUMBER": self.handle_number,
            "NEWLINE": self.handle_newline,
            "NL": self.handle_nl,               # ignore soft newlines
            "COMMENT": self.handle_comment,     # ignore comments
            "ENDMARKER": self.handle_endmarker,
        }

    def parse_file(self, src_path: Path):
        self.instructions.clear()
        self.current_op = None
        self.current_arg = None

        with src_path.open("rb") as f:
            for tok_info in tokenize(f.readline):
                self.process_token(tok_info)
        return self.instructions

    def process_token(self, tok_info: TokenInfo):
        # print(tok_info)  # uncomment to debug
        token_type_name = tok_name.get(tok_info.type, None)
        handler = self.handlers.get(token_type_name)
        if handler is not None:
            handler(tok_info)              # <<< pass the INSTANCE, not the class
        # else: silently ignore unknown token kinds

    # --- Handlers ---

    def handle_encoding(self, tok_info: TokenInfo):
        # ENCODING token’s .string is the codec name
        self.encoding = tok_info.string

    def handle_name(self, tok_info: TokenInfo):
        s = tok_info.string
        if s == "None":
            return self.handle_none(tok_info)
        # First NAME on a line = opcode
        if self.current_op is None:
            self.current_op = s
            return
        # If you later want NAME as an argument, you could set current_arg here.

    def handle_string(self, tok_info: TokenInfo):
        # Turn the Python string literal into a Python value
        try:
            self.current_arg = ast.literal_eval(tok_info.string)
        except Exception:
            # Fallback: keep raw token text (including quotes)
            self.current_arg = tok_info.string

    def handle_number(self, tok_info: TokenInfo):
        text = tok_info.string
        try:
            # int first, else float
            self.current_arg = int(text)
        except ValueError:
            try:
                self.current_arg = float(text)
            except ValueError:
                self.current_arg = text

    def handle_nl(self, tok_info: TokenInfo):
        # Soft newline inside a logical line: ignore
        pass

    def handle_comment(self, tok_info: TokenInfo):
        # Ignore comments entirely
        pass

    def handle_newline(self, tok_info: TokenInfo):
        # Logical line ends: store instruction if we have an op
        if self.current_op is not None:
            self.store_instruction()

    def handle_endmarker(self, tok_info: TokenInfo):
        # Flush any dangling op at EOF
        if self.current_op is not None:
            self.store_instruction()

    def handle_none(self, tok_info: TokenInfo):
        self.current_arg = ExplicitNone()

    def store_instruction(self):
        op = self.current_op
        arg = self.current_arg
        # Reset state early to avoid reentrancy surprises
        self.current_op = None
        self.current_arg = None

        if op is None:
            return

        # Be careful: keep zero/empty args; only treat missing arg as None
        if isinstance(arg, ExplicitNone):
            instr = Instr(op, None)
        elif arg is not None:
            instr = Instr(op, arg)
        else:
            instr = Instr(op)

        self.instructions.append(instr)

if __name__ == "__main__":
    path = Path("examples/printer.paxy")
    parser = Parser()
    instrs = parser.parse_file(path)
    print(instrs)
