from pathlib import Path
from bytecode import BinaryOp
from paxy.parser import Parser

def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]

def strip_frame(pairs):
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    if out and out[-1] == ("RETURN_CONST", None):
        out.pop()
    return out

def norm_arg(a):
    # Display BinaryOp enums as their names for stable comparison
    if isinstance(a, BinaryOp):
        return a.name
    return a

def norm_pairs(pairs):
    return [(n, norm_arg(a)) for (n, a) in pairs]

def test_dec_lowering(tmp_path: Path):
    src = tmp_path / "dec1.paxy"
    src.write_text("DEC x\nRETURN_CONST None\n")

    got = norm_pairs(strip_frame(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "x"),
        ("LOAD_CONST", 1),
        ("BINARY_OP", "SUBTRACT"),
        ("STORE_NAME", "x"),
    ]
