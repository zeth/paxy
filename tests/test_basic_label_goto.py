from pathlib import Path
import pytest
from paxy.assembler import assemble_file

def test_label_forward_goto_executes(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    src = tmp_path / "prog.paxy"
    src.write_text(
        "GOTO end\n"
        "PRINT 'skip'\n"
        "LABEL end\n"
        "PRINT 'done'\n"
    )
    code = assemble_file(src)
    exec(code, {"__name__": "__main__"})
    assert capsys.readouterr().out == "done\n"

def test_label_backward_goto_loops(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    # Simple countdown 3,2,1 using GOTO
    src = tmp_path / "loop.paxy"
    src.write_text(
        "LET n 3\n"
        "LABEL top\n"
        "LOAD_NAME 'print'\n"
        "PUSH_NULL\n"
        "LOAD_NAME 'n'\n"
        "CALL 1\n"
        "POP_TOP\n"
        "LOAD_NAME 'n'\n"
        "LOAD_CONST 1\n"
        "BINARY_OP '-'    # 3.13: or use the correct opcode if you want\n"
        "STORE_NAME 'n'\n"
        "LOAD_NAME 'n'\n"
        "POP_JUMP_IF_FALSE end   # if n == 0 break (you can add a macro later)\n"
        "GOTO top\n"
        "LABEL end\n"
    )
    # Note: The two conditional/jump lines above are illustrative. If you don't
    # have POP_JUMP_IF_FALSE macro yet, replace with raw CPython opcode lines.

    # Execute
    code = assemble_file(src)
    exec(code, {"__name__": "__main__"})
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["3", "2", "1"]

def test_label_errors(tmp_path: Path):
    src = tmp_path / "dup.paxy"
    src.write_text("LABEL x\nLABEL x\n")
    with pytest.raises(SyntaxError):
        assemble_file(src)

    src = tmp_path / "undef.paxy"
    src.write_text("GOTO nowhere\n")
    with pytest.raises(SyntaxError):
        assemble_file(src)
