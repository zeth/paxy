from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import ReturnMarker


class ReturnCommand(Command):
    """
    RET [value]
      - RET               -> RETURN_CONST None  (3.13 emits RETURN_CONST 0)
      - RET <expr>        -> push <expr>, RETURN_VALUE
    """

    COMMAND = "RET"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) == 0:
            self.ops.append(ReturnMarker(has_value=False, lineno=self.lineno))
            return
        if len(args) == 1:
            self._emit_load_for(args[0])
            self.ops.append(ReturnMarker(has_value=True, lineno=self.lineno))
            return
        raise SyntaxError("RET takes at most one argument")
