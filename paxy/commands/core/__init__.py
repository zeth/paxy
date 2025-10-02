from paxy.commands.base import CommandMap
from paxy.commands.core.compare import Compare
from paxy.commands.core.dec import Dec
from paxy.commands.core.ifjump import IfOp
from paxy.commands.core.igl import Igloo
from paxy.commands.core.inc import Inc
from paxy.commands.core.inop import InCommand, NotInCommand
from paxy.commands.core.isbop import IsNotCommand, IsCommand
from paxy.commands.core.let import Let
from paxy.commands.core.map import MapCommand
from paxy.commands.core.mad import Mad
from paxy.commands.core.par import Par
from paxy.commands.core.pnt import Print
from paxy.commands.core.inp import Input
from paxy.commands.core.importer import ImportSimple
from paxy.commands.core.gosub import Gosub
from paxy.commands.core.label import LabelCommand, GotoCommand
from paxy.commands.core.returnstmt import ReturnCommand
from paxy.commands.core.row import RowCommand
from paxy.commands.core.vec import (
    LenCommand,
    VAppendCommand,
    VPopCommand,
    VRemoveCommand,
    VReverseCommand,
    VecCommand,
)
from paxy.commands.core.mapdel import MapDel
from paxy.commands.core.convert import ToInt, ToFloat, ToStr

CORE_COMMANDS: CommandMap = {
    "PNT": Print,
    "LET": Let,
    "INP": Input,
    "IMP": ImportSimple,
    "GOS": Gosub,
    "LBL": LabelCommand,
    "GO": GotoCommand,
    "DEC": Dec,
    "CMP": Compare,
    "IS": IsCommand,
    "NIS": IsNotCommand,
    "IN": InCommand,
    "NIN": NotInCommand,
    "INC": Inc,
    "IF": IfOp,
    "ROW": RowCommand,
    "IGL": Igloo,
    "VEC": VecCommand,
    "MAP": MapCommand,
    "MAD": Mad,
    "MAL": MapDel,
    "RET": ReturnCommand,
    "PAR": Par,
    "TIN": ToInt,
    "TFL": ToFloat,
    "TST": ToStr,
    "VAP": VAppendCommand,
    "VOP": VPopCommand,
    "VEM": VRemoveCommand,
    "VER": VReverseCommand,
    "LEN": LenCommand,
}
