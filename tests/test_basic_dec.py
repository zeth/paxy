from pathlib import Path
from bytecode import BinaryOp
from paxy.compiler.parser import Parser


def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]


def strip_frame(pairs):
    out = list(pairs)
    if out and out[0] == ("RESUME", 0):
        out.pop(0)
    #  3.14+: epilogue is LOAD_CONST <value>; RETURN_VALUE (we strip it off)
    if len(out) >= 2 and out[-1][0] == "RETURN_VALUE" and out[-2][0] == "LOAD_CONST":
        out.pop()  # RETURN_VALUE
        out.pop()  # LOAD_CONST <value>
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
    src.write_text("DEC x\nLOAD_CONST None\nRETURN_VALUE\n")

    got = norm_pairs(strip_frame(as_pairs(Parser().parse_file(src))))
    assert got == [
        ("LOAD_NAME", "x"),
        ("LOAD_CONST", 1),
        ("BINARY_OP", "SUBTRACT"),
        ("STORE_NAME", "x"),
    ]
