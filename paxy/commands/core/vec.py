from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class VecCommand(Command):
    """
    VEC <name> [elem1 elem2 ...]
      -> <name> = [elem1, elem2, ...]
    Elements can be identifiers or literal constants.
    """

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("VEC expects: VEC <name> [elem ...]")
        dst = str(args[0])
        elems = args[1:]

        # Push each element (identifier -> LOAD_NAME, otherwise LOAD_CONST)
        for e in elems:
            self._emit_load_for(e)  # base helper you’re already using elsewhere

        # Build list and store
        self.add_op("BUILD_LIST", len(elems))
        self.add_op("STORE_NAME", dst)
