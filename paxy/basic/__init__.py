# paxy/basic/__init__.py
from __future__ import annotations

from typing import Any, Dict, Type
from bytecode import Instr

from paxy.basic.base import BasicOperation
from paxy.basic.dec import Dec
from paxy.basic.let import Let
from paxy.basic.print import Print
from paxy.basic.input import Input
from paxy.basic.importer import ImportSimple
from paxy.basic.callfn import CallFn
from paxy.basic.label import LabelOp, GotoOp

BASIC_OPS: Dict[str, Type[BasicOperation]] = {
    "PRINT": Print,
    "LET": Let,
    "INPUT": Input,
    "IMPORT": ImportSimple,  # NEW
    "CALLFN": CallFn,  # NEW (avoid clash with native CALL opcode)
    "LABEL": LabelOp,
    "GOTO": GotoOp,
    "DEC": Dec,
}


def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS


def basic_op(op_name: str, op_args: list[Any], lineno: int) -> list[Instr]:
    cls = BASIC_OPS[op_name]
    inst = cls(op_args, lineno)
    return inst.ops
