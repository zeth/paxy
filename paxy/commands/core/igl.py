# paxy/basic/igl.py
"""
IGL <name> [elem1 elem2 ...]  -> name = frozenset({elem1, ...})
Fast path: all literals & hashable -> LOAD_CONST frozenset(...)
Fallback: mixed -> LOAD_NAME 'frozenset'; LOAD_*...; BUILD_TUPLE N; CALL 1
"""

from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class Igloo(Command):
    """Group several things together.

    # IGL — build a container (Igloo)

    So far, we've seen simple values: numbers, strings, floats.
    But programs often need to **group multiple values together**.

    Paxy's first container is the **Igloo**.

    It contains as many values as you want, but each element is unique.
    If you add two of the same thing, you only get one inside the Igloo,
    the other one is silently thrown out into the cold,
    never to be seen again.

    The order of the items doesn't matter.

    That makes it perfect for grouping things you just want
    to **keep together and test membership**.

    Once created, it cannot be changed (it's frozen).
    If you want to add or remove items, you have to make it again.

    ---

    ## Syntax

    ```paxy
    IGL <name> [elem1 elem2 ...]
    ```

    This creates an igloo and stores it in `<name>`.

    ---

    ## Examples

    ### An igloo of animals

    ```paxy
    IGL animals "cat" "dog" "bat"
    PNT animals
    ```

    Output:
    ```
    {'cat', 'dog', 'bat'}
    ```

    ### An igloo of integers

    ```paxy
    IGL prime 2 3 5 7 11 13 17 19
    LET isprime 2 in prime
    PNT isprime  # True
    ```

    ---

    ### Membership test with `in`

    You can use `in` and `not in` operators (from [LET](let)) to check if something is in the Igloo:

    ```paxy
    IGL animals "cat" "dog" "bat"
    LET hasdog "dog" in animals
    PNT hasdog    # True
    ```

    ---

    ### Mixing variables and literals

    You can also include variables:

    ```paxy
    LET x "apple"
    IGL basket x "banana" "cherry"
    PNT basket
    ```

    ---

    ### Advanced detail

    It's currently implemented in the compiler as a frozenset, this could change.

    ---

    ## Summary

    - IGL makes a container for multiple values.
    - Unique, unordered, frozen — great for membership tests.
    - Works with literals or variables.


    ## Would you like to know more?

    The IGL has a lot of contraints. Let's start removing them.
    Sometimes you **want duplicates** and **care about order**.
    That's where [ROW](row.md) comes in.

    """

    COMMAND = "IGL"

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("IGL expects: IGL <name> [elem ...]")
        dst_ident = str(args[0])
        elems = args[1:]

        # Fast path: all literals and hashable
        if all(not isinstance(e, Ident) for e in elems):
            try:
                konst = frozenset(elems)
            except TypeError as exc:
                # unhashable literal (e.g., list) — must use fallback
                konst = None
            if konst is not None:
                self.add_op("LOAD_CONST", konst)
                self.add_op("STORE_NAME", dst_ident)
                return

        # Fallback: build at runtime via function call
        # Stack order for CALL: push callable first, then arguments
        self.add_op("LOAD_NAME", "frozenset")
        for e in elems:
            self._emit_load_for(e)
        self.add_op("BUILD_TUPLE", len(elems))  # frozenset(iterable)
        self.add_op("CALL", 1)
        self.add_op("STORE_NAME", dst_ident)
