from typing import Any
from paxy.commands.base import Command


class Print(Command):
    """Print a value (or nothing at all) to the screen.

    This is the easiest way to get feedback from your program.

    `PRINT [value]`

    ---

    ## Basics

    If you write `PRINT` on its own, it shows a blank line:

    ```paxy
    PRINT
    ```

    ---

    ## Printing text

    You can show words or sentences by quoting them:

    ```paxy
    PRINT "Hello, world!"
    PRINT "Paxy makes coding calm."
    ```

    ---

    ## Printing numbers

    Numbers can be printed directly:

    ```paxy
    PRINT 42
    PRINT 3.14
    ```

    ---

    ## Printing variables

    If you have stored something in a variable with `LET`, you can show it:

    ```paxy
    LET name "Alice"
    PRINT name

    LET total 123
    PRINT total
    ```

    ---

    ## Printing results of expressions

    You can even print the outcome of a calculation:

    ```paxy
    PRINT 5 + 7       # shows 12
    PRINT 10 * 3      # shows 30
    ```

    ---

    ## Putting it together

    Here’s a small example that combines `LET` and `PRINT`:

    ```paxy
    LET a 10
    LET b 20
    LET sum a + b
    PRINT "The total is:"
    PRINT sum
    ```

    This shows:

    ```
    The total is:
    30
    ```

    ---

    **Summary**:
    - `PRINT` with nothing → blank line
    - `PRINT "..."` → text
    - `PRINT number` → numbers
    - `PRINT variable` → variables
    - `PRINT expression` → results of calculations

    ## Would you like to know more?

    We saw how PRINT sends information from the program to the human,
    let's look at how to send text from the human to the program with the [INPUT](input.md) command.

    """

    COMMAND = "PRINT"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) > 1:
            raise SyntaxError("PRINT takes at most one argument")

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
