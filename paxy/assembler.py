# paxy/assembler.py
import dis
from types import CodeType
import types

def assemble_file(src_path) -> types.CodeType:
    """
    Stub assembler for Python 3.13+: return a no-op module CodeType.
    Emits: RESUME 0 ; LOAD_CONST None ; RETURN_VALUE
    """
    # Bytecode
    code_bytes = bytes([
        dis.opmap['RESUME'], 0,
        dis.opmap['LOAD_CONST'], 0,
        dis.opmap['RETURN_VALUE'], 0,
    ])

    consts = (None,)         # co_consts[0] = None
    names = ()               # no names
    varnames = ()            # no fast locals
    filename = str(src_path) # for tracebacks
    name = "<module>"
    qualname = "<module>"    # NEW in 3.13 constructor order
    firstlineno = 1
    linetable = b'\x00'      # minimal, valid single-line table
    exceptiontable = b''     # none
    flags = 0x0040           # CO_NOFREE
    stacksize = 1
    nlocals = 0
    posonly = 0
    kwonly = 0
    argcount = 0

    # 3.13 constructor order:
    # (argcount, posonlyargcount, kwonlyargcount, nlocals, stacksize, flags,
    #  code, consts, names, varnames, filename, name, qualname,
    #  firstlineno, linetable, exceptiontable, freevars, cellvars)
    code = CodeType(
        argcount,
        posonly,
        kwonly,
        nlocals,
        stacksize,
        flags,
        code_bytes,
        consts,
        names,
        varnames,
        filename,
        name,
        qualname,
        firstlineno,
        linetable,
        exceptiontable,
        (),  # freevars
        (),  # cellvars
    )
    return code
