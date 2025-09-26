# paxy/basic/__init__.py
from __future__ import annotations

from typing import Any, Dict, Type, Union, List
from bytecode import Instr

from paxy.basic.base import BasicOperation, BasicItem
from paxy.basic.compare import CompareOp
from paxy.basic.dec import Dec
from paxy.basic.ifjump import IfOp
from paxy.basic.igl import IglOp
from paxy.basic.inc import IncOp
from paxy.basic.inop import InOp, NotInOp
from paxy.basic.isbop import IsNotOp, IsBop
from paxy.basic.let import Let
from paxy.basic.map import MapOp
from paxy.basic.mapadd import MapAddOp
from paxy.basic.print import Print
from paxy.basic.input import Input
from paxy.basic.importer import ImportSimple
from paxy.basic.gosub import Gosub
from paxy.basic.label import LabelOp, GotoOp
from paxy.basic.returnstmt import ReturnOp
from paxy.basic.row import RowOp
from paxy.basic.vec import VecOp
from paxy.basic.mapdel import MapDelOp

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
}


def is_basic_op(op_name: str) -> bool:
    return op_name in BASIC_OPS


def basic_op(op_name: str, op_args: list[Any], lineno: int) -> List[BasicItem]:
    cls = BASIC_OPS[op_name]
    inst = cls(op_args, lineno)
    return inst.ops
