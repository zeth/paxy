# paxy/basic/__init__.py
from __future__ import annotations

from typing import Any, Dict, Type, Union, List
from dis import opmap
from bytecode import Instr

from paxy.commands.base import BasicOperation, BasicItem
from paxy.commands.compare import CompareOp
from paxy.commands.dec import Dec
from paxy.commands.ifjump import IfOp
from paxy.commands.igl import IglOp
from paxy.commands.inc import IncOp
from paxy.commands.inop import InOp, NotInOp
from paxy.commands.isbop import IsNotOp, IsBop
from paxy.commands.let import Let
from paxy.commands.map import MapOp
from paxy.commands.mapadd import MapAddOp
from paxy.commands.par import Par
from paxy.commands.print import Print
from paxy.commands.input import Input
from paxy.commands.importer import ImportSimple
from paxy.commands.gosub import Gosub
from paxy.commands.label import LabelOp, GotoOp
from paxy.commands.returnstmt import ReturnOp
from paxy.commands.row import RowOp
from paxy.commands.vec import VecOp
from paxy.commands.mapdel import MapDelOp

BLOCK_OPS = {"SUB", "SUBEND", "RANGE", "RANGEEND"}

BASIC_OPS: Dict[str, Type[BasicOperation]] = {
    "PRINT": Print,
    "LET": Let,
    "INPUT": Input,
    "IMPORT": ImportSimple,  # NEW
    "GOSUB": Gosub,  # NEW (avoid clash with native CALL opcode)
    "LABEL": LabelOp,
    "GOTO": GotoOp,
    "DEC": Dec,
    "COMPARE": CompareOp,
    "IS": IsBop,
    "ISNOT": IsNotOp,
    "IN": InOp,
    "NOTIN": NotInOp,
    "INC": IncOp,
    "IF": IfOp,
    "ROW": RowOp,
    "IGL": IglOp,
    "VEC": VecOp,
    "MAP": MapOp,
    "MAPADD": MapAddOp,
    "MAPDEL": MapDelOp,
    "RETURN": ReturnOp,
    "PAR": Par,
}


def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS


VALID_OPS = set(opmap) | set(BASIC_OPS) | BLOCK_OPS


def is_opcode_name(op_name: str) -> bool:
    return op_name in VALID_OPS


def basic_op(op_name: str, op_args: list[Any], lineno: int) -> List[BasicItem]:
    cls = BASIC_OPS[op_name]
    inst = cls(op_args, lineno)
    return inst.ops
