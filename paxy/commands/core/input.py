from typing import Any
from paxy.commands.base import Command
from paxy.compiler.ir import Ident


class Input(Command):
    """Read a value from the user.

    ```
    INPUT <name>
    ```

    The `INPUT` command pauses the program and asks the user to type something.
    Whatever the user types is stored in the variable `<name>`.

    ---

    ## Basics

    ```paxy
    INPUT name
    PRINT name
    ```

    When run, the program will wait for you to type.
    If you type `Alice` then hit enter, the output will be:

    ```
    Alice
    ```

    ---

    ## Using INPUT with numbers

    By default, everything typed with `INPUT` is text (a "string").
    If you want a number, you can convert it afterwards:

    ```paxy
    INPUT age
    TOINT age age    # convert text to an integer
    PRINT age
    ```

    If you type `42`, the output is:

    ```
    42
    ```

    ---

    ## Combine with LET

    You can use `INPUT` and `LET` together to do calculations:

    ```paxy
    INPUT a
    INPUT b
    TOINT a a
    TOINT b b
    LET total a + b
    PRINT total
    ```

    If you type `10` and `32`, the output is:

    ```
    42
    ```

    ---

    ## Example: Greeting

    ```paxy
    PRINT "What is your name?"
    INPUT name
    PRINT "Hello,"
    PRINT name
    ```

    If you type `Charlie`, the output is:

    ```
    What is your name?
    Hello,
    Charlie
    ```

    Input reads from what we call stdin ("standard in"),
    which for simplicy's sake is the normally the keyboard
    (but in more advanced usage could be another program,
    don't worry about that).

    ## Would you like to know more?

    In those examples above, we saw an extra command used.
    Let's look at [TOINT](../commands/toint.md) next.
    """

    COMMAND = "INPUT"

    def make_ops(self, op_args: list[Any]) -> None:
        if len(op_args) != 1:
            raise SyntaxError("INPUT takes exactly one identifier")
        name = op_args[0]
        if not isinstance(name, Ident):
            raise SyntaxError("INPUT expects an identifier")
        self.add_op("LOAD_NAME", "input")
        self.add_op("PUSH_NULL")
        self.add_op("CALL", 0)
        self.add_op("STORE_NAME", str(name))
