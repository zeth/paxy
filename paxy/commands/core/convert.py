from __future__ import annotations
from typing import Any

from bytecode import Instr  # type: ignore[import-untyped]
from paxy.commands.base import Command
from paxy.compiler.ir import Ident

__all__ = ["ToInt", "ToFloat", "ToStr"]


class _ConvertBase(Command):
    CATEGORY = "core"

    def _emit_load_token(self, tok: Any) -> None:
        if isinstance(tok, Ident):
            # Module-level will be LOAD_NAME; your function rewriter will turn
            # these into LOAD_FAST inside SUB bodies.
            self.add_op("LOAD_NAME", str(tok))
        else:
            self.add_op("LOAD_CONST", tok)

    def _emit_store_name(self, ident: Ident) -> None:
        self.add_op("STORE_NAME", str(ident))


class ToInt(_ConvertBase):
    """Convert a value to an integer (whole number).

    **Syntax:**

    ```paxy
    TOINT <dst> <src>
    ```

    - `<dst>` is the variable where the result will be stored.
    - `<src>` is the value or variable to convert.

    ---

    ## What are types?

    In programming, every value has a **type**. Examples:

    - `"42"` is a string (text).
    - `42` is an integer (whole number).
    - `3.14` is a float (decimal number).

    Sometimes we need to convert between them. For example, `INPUT` always gives you a string, but if you want to do arithmetic, you need an integer.

    ---

    ## Examples

    ### Convert input to integer

    ```paxy
    INPUT a
    TOINT a a
    LET b 10
    LET sum a + b
    PRINT sum
    ```

    If the user types `32`, the program prints `42`.

    ---

    ### Convert a float string

    ```paxy
    LET x "3.9"
    TOFLOAT f x
    TOINT n f
    PRINT n      # 3
    ```

    ### Would you like to know more?

    We turned text into numbers,
    now let's go the other way with [TOSTR](../commands/tostr.md) next.
    """

    COMMAND = "TOINT"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2 or not isinstance(args[0], Ident):
            raise SyntaxError("TOINT: usage: TOINT <dst> <src>")
        dst, src = args  # type: ignore[misc]
        self.add_op("LOAD_GLOBAL", (True, "int"))
        self._emit_load_token(src)
        self.add_op("CALL", 1)
        self._emit_store_name(dst)


class ToFloat(_ConvertBase):
    """Convert a value to a floating‑point number (decimal).

    **Syntax:**

    ```paxy
    TOFLOAT <dst> <src>
    ```

    - `<dst>` is the variable where the result will be stored.
    - `<src>` is the value or variable to convert.

    ---

    ## Why?

    See [TOINT](toint.md) for an explanation of types.
    `TOFLOAT` is useful when you need decimal precision instead of integers.

    ---

    ## Examples

    ```paxy
    INPUT value
    TOFLOAT f value
    LET doubled f * 2
    PRINT doubled
    ```

    ```paxy
    LET s "2.718"
    TOFLOAT e s
    PRINT e
    ```

    ### Would you like to know more?

    We have been dealing with text strings, integer numbers, and floats.
    Now let's look at our first container type, our first group of elements,
    with the [IGL](../commands/igl.md).

    """

    COMMAND = "TOFLOAT"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2 or not isinstance(args[0], Ident):
            raise SyntaxError("TOFLOAT: usage: TOFLOAT <dst> <src>")
        dst, src = args  # type: ignore[misc]
        self.add_op("LOAD_GLOBAL", (True, "float"))
        self._emit_load_token(src)
        self.add_op("CALL", 1)
        self._emit_store_name(dst)


class ToStr(_ConvertBase):
    """Convert a value to a string (text).

    **Syntax:**

    ```paxy
    TOSTR <dst> <src>
    ```

    - `<dst>` is the variable where the result will be stored.
    - `<src>` is the value or variable to convert.

    ---

    ## Why?

    See [TOINT](toint.md) for an explanation of types.
    `TOSTR` is useful when you want to turn numbers into text.

    ---

    ## Examples

    ```paxy
    LET score 99
    TOSTR msg score
    PRINT msg       # "99"
    ```

    ```paxy
    LET pi 3.14
    TOSTR txt pi
    PRINT txt       # "3.14"
    ```

    ## Would you like to know more?

    We have another command that follows a similar idea: [TOFLOAT](../commands/tofloat.md).

    """

    COMMAND = "TOSTR"

    def make_ops(self, args: list[Any]) -> None:
        if len(args) != 2 or not isinstance(args[0], Ident):
            raise SyntaxError("TOSTR: usage: TOSTR <dst> <src>")
        dst, src = args  # type: ignore[misc]
        self.add_op("LOAD_GLOBAL", (True, "str"))
        self._emit_load_token(src)
        self.add_op("CALL", 1)
        self._emit_store_name(dst)
