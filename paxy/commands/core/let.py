# paxy/basic/let.py
from typing import Any, Tuple
from paxy.commands.base import Command
from paxy.compiler.ir import Ident
from paxy.compiler.opcoerce import (
    coerce_binary_op,
    coerce_compare_op,
    coerce_contains_op,
    coerce_is_op,
)


class Let(Command):
    """Assign a value. Also supports operators: arithmetic, comparison, `is`, `in`, etc.

    ```
    LET <name> <value>
    LET <name> <lhs> <op> <rhs>
    # op: +, -, *, //, ==, <=, is, in, not in, etc.
    ```

    ## Simple assignments

    The most basic form of `LET` just gives a name to a value.
    This lets you store numbers, text, or other data for later use.

    ```paxy
    LET x 5
    LET name "Alice"
    ```

    You can also copy the value of another variable into a new one:

    ```paxy
    LET y x
    ```

    ---

    ## Operator assignments

    `LET` can also perform a calculation or check between two values
    and store the result.

    ### Arithmetic

    These are the standard maths operators: add, subtract, multiply, divide, etc.

    ```paxy
    LET a 7
    LET b 3

    LET result a + b        # 10
    LET answer a - b        # 4
    LET product a * b       # 21
    LET div a / b           # 2.333...
    LET floordiv a // b     # 2
    LET mod a % b           # 1
    LET power a ** b        # 343
    ```

    Divide in computing is a forward slash not a ÷. Think of a fraction, e.g. half is 1/2.

    ---

    ### Comparisons

    Comparisons let you test relationships between values.
    The result is always `True` or `False`.

    ```paxy
    LET x 5
    LET y 8

    LET eq x == y        # False
    LET ne x != y        # True
    LET lt x < y         # True
    LET le x <= y        # True
    LET gt x > y         # False
    LET ge x >= y        # False
    ```

    ---

    ### Identity

    Identity checks whether two variables actually point to the same object in memory.
    This is different from equality (`==`), which only compares values.

    ```paxy
    LET a None
    LET b None
    LET c 0

    LET same a is b         # True
    LET notsame a is not c  # True
    ```

    ---

    ### Membership

    Membership checks if a value is inside a collection such as a list.

    ```paxy
    LET animals ["cat", "dog", "bat"]

    LET hasdog "dog" in animals       # True
    LET hasnemo "nemo" not in animals # True
    ```

    ---

    ### Bitwise

    Bitwise operators work directly on the binary digits of numbers.
    They’re less common for beginners, but useful for low-level tasks.

    ```paxy
    LET x 6     # 110 in binary
    LET y 3     # 011 in binary

    LET anded x & y     # 2  (010)
    LET ored  x | y     # 7  (111)
    LET xor   x ^ y     # 5  (101)
    LET shl   x << 1    # 12 (1100)
    LET shr   x >> 1    # 3  (011)
    ```

    If you don't understand this, just ignore it.
    If you ever get to the point of wanting to use them,
    then you will understand what they do.

    ---

    ## Examples

    ### Add numbers

    Here we add two numbers and print the result:

    ```paxy
    LET x 10
    LET y 20
    LET total x + y
    PNT total     # 30
    ```

    ### Compare strings

    Equality also works on text:

    ```paxy
    LET a "cat"
    LET b "dog"
    LET same a == b
    PNT same      # False
    ```

    ### Check membership

    A [vector](vec.md) can be searched with `in` and `not in`:

    ```paxy
    LET animals ["cat", "dog", "bat"]
    LET hasdog "dog" in animals
    PNT hasdog    # True
    ```

    ### Identity test

    `is` checks whether two variables are the *same object*, not just equal in value:

    ```paxy
    LET x None
    LET y None
    LET same x is y
    PNT same      # True
    ```

    ### Would you like to know more?

    Let's look at [PNT](pnt.md).
    """

    COMMAND = "LET"

    def make_ops(self, args: list[Any]) -> None:
        dst_ident, rest = self._parse_head(args)

        if len(rest) == 1:
            self._emit_simple_assignment(dst_ident, rest[0])
            return

        if len(rest) == 3:
            lhs, op, rhs = rest
            self._emit_operator_assignment(dst_ident, lhs, op, rhs)
            return

        raise SyntaxError("LET operator form: LET <name> <lhs> <op> <rhs>")

    # ---------- parsing / validation ----------

    def _parse_head(self, args: list[Any]) -> tuple[Ident, list[Any]]:
        if len(args) < 2:
            raise SyntaxError("LET expects at least: LET <name> <value>")
        name = args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("LET expects an identifier as the first argument")
        return name, args[1:]

    # ---------- simple form ----------

    def _emit_simple_assignment(self, dst_ident: Ident, value: Any) -> None:
        self._emit_load(value)
        self._emit_store(dst_ident)

    # ---------- operator form ----------

    def _emit_operator_assignment(
        self, dst_ident: Ident, lhs: Any, op: Any, rhs: Any
    ) -> None:
        self._emit_load(lhs)
        self._emit_load(rhs)
        kind, coerced = self._classify_and_coerce_op(op)
        self._emit_op(kind, coerced)
        self._emit_store(dst_ident)

    # ---------- tiny primitives ----------

    def _emit_load(self, value: Any) -> None:
        if isinstance(value, Ident):
            self.add_op("LOAD_NAME", str(value))
        else:
            self.add_op("LOAD_CONST", value)

    def _emit_store(self, ident: Ident) -> None:
        self.add_op("STORE_NAME", str(ident))

    # ---------- operator classification ----------

    def _classify_and_coerce_op(self, op: Any) -> Tuple[str, Any]:
        """
        Try comparison → identity → membership → binary.
        Returns (kind, coerced_arg) where kind ∈ {"COMPARE_OP","IS_OP","CONTAINS_OP","BINARY_OP"}.
        """
        text = str(op)

        # comparisons: == != < <= > >=
        try:
            return "COMPARE_OP", coerce_compare_op(text)
        except SyntaxError:
            pass

        # identity: is / is not
        try:
            return "IS_OP", coerce_is_op(text)
        except SyntaxError:
            pass

        # membership: in / not in
        try:
            return "CONTAINS_OP", coerce_contains_op(text)
        except SyntaxError:
            pass

        # fall back to binary arithmetic/bitwise
        return "BINARY_OP", coerce_binary_op(text)

    def _emit_op(self, kind: str, coerced: Any) -> None:
        # All these opcodes take exactly one argument
        self.add_op(kind, coerced)
