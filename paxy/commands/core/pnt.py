from typing import Any
from paxy.commands.base import Command


class Print(Command):
    """Print a value (or nothing at all) to the screen.

    This is the easiest way to get feedback from your program.

    `PNT [value]`

    ---

    ## Basics

    If you write `PNT` on its own, it shows a blank line:

    ```paxy
    PNT
    ```

    ---

    ## Printing text

    You can show words or sentences by quoting them:

    ```paxy
    PNT "Hello, world!"
    PNT "Paxy makes coding calm."
    ```

    ---

    ## Printing numbers

    Numbers can be printed directly:

    ```paxy
    PNT 42
    PNT 3.14
    ```

    ---

    ## Printing variables

    If you have stored something in a variable with `LET`, you can show it:

    ```paxy
    LET name "Alice"
    PNT name

    LET total 123
    PNT total
    ```

    ---

    ## Printing results of expressions

    You can even print the outcome of a calculation:

    ```paxy
    PNT 5 + 7       # shows 12
    PNT 10 * 3      # shows 30
    ```

    ---

    ## Putting it together

    Here’s a small example that combines `LET` and `PNT`:

    ```paxy
    LET a 10
    LET b 20
    LET sum a + b
    PNT "The total is:"
    PNT sum
    ```

    This shows:

    ```
    The total is:
    30
    ```

    ---

    **Summary**:
    - `PNT` with nothing → blank line
    - `PNT "..."` → text
    - `PNT number` → numbers
    - `PNT variable` → variables
    - `PNT expression` → results of calculations

    ## Would you like to know more?

    We saw how PNT sends information from the program to the human,
    let's look at how to send text from the human to the program with the [INP](inp.md) command.

    """

    COMMAND = "PNT"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) > 1:
            raise SyntaxError("PNT takes at most one argument")

        # Load builtin print and prepare CALL convention
        self.add_op("LOAD_NAME", "print")
        self.add_op("PUSH_NULL")

        if len(op_args) == 0:
            # print()
            self.add_op("CALL", 0)
        else:
            # print(<arg>) — load identifier as name, literal as const
            self._emit_load_for(op_args[0])
            self.add_op("CALL", 1)

        self.add_op("POP_TOP")
