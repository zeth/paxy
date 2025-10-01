"""
VEC <name> [elem1 elem2 ...]
-> <name> = [elem1, elem2, ...]
Elements can be identifiers or literal constants.
"""

from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class VecCommand(Command):
    """Create a vector (mutable collection).

    VEC <name> [elem1 elem2 ...]
      -> <name> = [elem1, elem2, ...]
    """

    COMMAND = "VEC"

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("VEC expects: VEC <name> [elem ...]")
        dst = str(args[0])
        elems = args[1:]

        for e in elems:
            self._emit_load_for(e)
        self.add_op("BUILD_LIST", len(elems))
        self.add_op("STORE_NAME", dst)


class AppendCommand(Command):
    """Append an element to a vector.

    APPEND <vec> <elem>
      -> <vec>.append(<elem>)
    """

    COMMAND = "APPEND"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2:
            raise SyntaxError("APPEND expects: APPEND <vec> <elem>")
        vec, elem = args
        self.add_op("LOAD_NAME", str(vec))
        self._emit_load_for(elem)
        self.add_op("LIST_APPEND", 1)


class PopCommand(Command):
    """Remove and return the last element (or by index).

    POP <dst> <vec> [index]
      -> <dst> = <vec>.pop([index])
    """

    COMMAND = "POP"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) not in (2, 3):
            raise SyntaxError("POP expects: POP <dst> <vec> [index]")
        dst, vec, *opt_index = args
        self.add_op("LOAD_NAME", str(vec))
        if opt_index:
            self._emit_load_for(opt_index[0])
            self.add_op("CALL_METHOD", ("pop", 1))
        else:
            self.add_op("CALL_METHOD", ("pop", 0))
        self.add_op("STORE_NAME", str(dst))


class RemoveCommand(Command):
    """Remove the first matching element.

    REMOVE <vec> <elem>
      -> <vec>.remove(<elem>)
    """

    COMMAND = "REMOVE"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2:
            raise SyntaxError("REMOVE expects: REMOVE <vec> <elem>")
        vec, elem = args
        self.add_op("LOAD_NAME", str(vec))
        self._emit_load_for(elem)
        self.add_op("CALL_METHOD", ("remove", 1))


class ReverseCommand(Command):
    """Reverse a vector in place.

    REVERSE <vec>
      -> <vec>.reverse()
    """

    COMMAND = "REVERSE"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 1:
            raise SyntaxError("REVERSE expects: REVERSE <vec>")
        vec = args[0]
        self.add_op("LOAD_NAME", str(vec))
        self.add_op("CALL_METHOD", ("reverse", 0))


class LenCommand(Command):
    """Get the length of a vector.

    LEN <dst> <vec>
      -> <dst> = len(<vec>)
    """

    COMMAND = "LEN"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2:
            raise SyntaxError("LEN expects: LEN <dst> <vec>")
        dst, vec = args
        self.add_op("LOAD_GLOBAL", (True, "len"))
        self.add_op("LOAD_NAME", str(vec))
        self.add_op("CALL", 1)
        self.add_op("STORE_NAME", str(dst))
