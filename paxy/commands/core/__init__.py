from paxy.commands.base import CommandMap
from paxy.commands.core.compare import CompareOp
from paxy.commands.core.dec import Dec
from paxy.commands.core.ifjump import IfOp
from paxy.commands.core.igl import IglOp
from paxy.commands.core.inc import IncOp
from paxy.commands.core.inop import InOp, NotInOp
from paxy.commands.core.isbop import IsNotOp, IsBop
from paxy.commands.core.let import Let
from paxy.commands.core.map import MapOp
from paxy.commands.core.mapadd import MapAddOp
from paxy.commands.core.par import Par
from paxy.commands.core.print import Print
from paxy.commands.core.input import Input
from paxy.commands.core.importer import ImportSimple
from paxy.commands.core.gosub import Gosub
from paxy.commands.core.label import LabelOp, GotoOp
from paxy.commands.core.returnstmt import ReturnOp
from paxy.commands.core.row import RowOp
from paxy.commands.core.vec import VecOp
from paxy.commands.core.mapdel import MapDelOp


CORE_COMMANDS: CommandMap = {
    "PRINT": Print,
    "LET": Let,
    "INPUT": Input,
    "IMPORT": ImportSimple,
    "GOSUB": Gosub,
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
