# paxy/assembler.py
import dis
from bytecode import Instr, Bytecode, CompilerFlags

def assemble_file(src_path):
    """
    Python 3.13: print('hello')
      RESUME 0
      LOAD_NAME 'print'
      PUSH_NULL
      LOAD_CONST 'hello'
      CALL 1
      POP_TOP
      RETURN_CONST None    # or LOAD_CONST None ; RETURN_VALUE if RETURN_CONST not available
    """
    bc = Bytecode()
    bc.filename = str(src_path)
    bc.name = "<module>"
    bc.first_lineno = 1
    bc.flags |= CompilerFlags.NOFREE

    ops = [
        Instr("RESUME", 0),
        Instr("LOAD_NAME", "print"),
    ]

    # 3.11+ calling convention helpers
    if "PUSH_NULL" in dis.opmap:
        ops.append(Instr("PUSH_NULL"))

    ops += [
        Instr("LOAD_CONST", "hello"),
        Instr("CALL", 1),          # 1 positional arg
        Instr("POP_TOP"),
    ]

    if "RETURN_CONST" in dis.opmap:
        # 3.13 has RETURN_CONST; arg is the constant value
        ops.append(Instr("RETURN_CONST", None))
    else:
        ops += [Instr("LOAD_CONST", None), Instr("RETURN_VALUE")]

    bc.extend(ops)
    return bc.to_code()
