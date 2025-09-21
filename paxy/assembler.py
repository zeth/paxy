# paxy/assembler.py
from __future__ import annotations

from pathlib import Path
from bytecode import Bytecode, CompilerFlags
from types import CodeType

from .parser import Parser


def assemble_file(src_path: Path) -> CodeType:
    """
    Assemble a .paxy file into a module CodeType by:
      1) Parsing to a list of bytecode.Instr
      2) Wrapping in a Bytecode object
      3) Setting metadata (filename, first line, flags)
      4) Converting to a CodeType
    """
    parser = Parser()
    instrs = parser.parse_file(src_path)

    bc = Bytecode(instrs)
    bc.filename = str(src_path)
    bc.name = "<module>"
    # Use the first instruction's lineno if present; else default to 1
    try:
        first = next(i for i in instrs if getattr(i, "lineno", None))
        bc.first_lineno = first.lineno
    except StopIteration:
        bc.first_lineno = 1

    # Safe default: module has no free vars
    bc.flags |= CompilerFlags.NOFREE

    return bc.to_code()
