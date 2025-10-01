# paxy/basic/row.py
"""
ROW <name> [elem1 elem2 ...]  -> name = (elem1, elem2, ...)
Fast path: all literals -> LOAD_CONST (tuple)
Fallback: mixed idents/literals -> LOAD_*...; BUILD_TUPLE N
"""


from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class RowCommand(Command):
    """Create a row (ordered collection of elements).

    A **ROW** is an ordered set of values saved under a name:
    - **Ordered**: items keep their position.
    - **Duplicates allowed**: `("cat", "cat")` is fine.
    - **Immutable**: like IGL, a ROW can’t be changed in-place. To “update”, build a new one.

    ---

    ## Syntax

    ```paxy
    ROW <name> [elem1 elem2 ...]
    ```

    - If all elements are literals, Paxy emits a fast constant tuple.
    - If you mix variables and literals, it builds the tuple on the stack.

    ---

    ## Examples

    ### Build a simple row

    ```paxy
    ROW pair 1 2
    PNT pair
    ```

    Output:
    ```
    (1, 2)
    ```

    ---

    ### Duplicates and order

    ```paxy
    ROW coords 0 0 10 10
    PNT coords    # (0, 0, 10, 10)
    ```

    ---

    ### Mix variables and literals

    ```paxy
    LET x 42
    ROW triple x "answer" 3.14
    PNT triple          # (42, "answer", 3.14)
    ```

    ---

    ### Membership test with `in`

    You can use `in` / `not in` just like with IGL (it checks for an *element* inside the row):

    ```paxy
    ROW animals "cat" "dog" "bat" "dog"
    LET hasdog "dog" in animals
    PNT hasdog          # True
    ```

    ### Rebuild to “change” a row

    Rows are immutable. To “modify” one, create a new row from parts:

    ```paxy
    ROW r 1 2 3
    ROW r2 0 r 4      # (0, (1, 2, 3), 4) — nested
    ```
    If you want to flatten it, build it explicitly:
    ```paxy
    LET a 1
    LET b 2
    LET c 3
    ROW r2 0 a b c 4  # (0, 1, 2, 3, 4)
    ```

    ---

    ## How ROW compares to IGL

    | Feature      | IGL              | ROW                 |
    |--------------|------------------|---------------------|
    | Order        | No               | **Yes**             |
    | Duplicates   | No               | **Yes**             |
    | Mutable?     | No               | No                  |
    | Best for     | membership tests | **fixed sequences** |

    ---

    ## Would you like to know more?

    Sometimes you need a **mutable** ordered collection.
    Next, meet a vector (a dynamic container you can grow and change).
    See [VEC](vec.md).
    """

    COMMAND = "ROW"

    def make_ops(self, args: list[Any]) -> None:
        if not args or not isinstance(args[0], Ident):
            raise SyntaxError("ROW expects: ROW <name> [elem ...]")
        dst_ident = str(args[0])
        elems = args[1:]

        # Fast path: all literals
        if all(not isinstance(e, Ident) for e in elems):
            self.add_op("LOAD_CONST", tuple(elems))
            self.add_op("STORE_NAME", dst_ident)
            return

        # Fallback: builder path
        for e in elems:
            self._emit_load_for(e)
        self.add_op("BUILD_TUPLE", len(elems))
        self.add_op("STORE_NAME", dst_ident)
