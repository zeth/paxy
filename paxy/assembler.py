# paxy/assembler.py
import types

def assemble_file(src_path) -> types.CodeType:
    """
    Stub for Python 3.13: return a module CodeType that prints 'hello'.
    Using compile() guarantees a valid linetable/exception table for 3.13.
    """
    source = "print('hello')\n"
    # filename only affects tracebacks; use the actual path for nicer errors
    return compile(source, str(src_path), "exec")
