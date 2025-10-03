# Paxy — code in calm

Beginner's All-purpose Symbolic Instruction Code taught millions their first programs in the 1970s and 1980s.

Paxy revives the spirit of BASIC — not just as nostalgia, but as a deliberate choice: a simpler way to code.  
Every line is a single command with arguments.

Where modern programming piles on frameworks, boilerplate, and ceremony, Paxy takes the opposite path.

- **Simplicity first.** A few clear commands (`LET`, `IF`, `PNT`, `RNG`) are enough to get started.
- **Immediate feedback.** Programs run top-to-bottom, exactly as written.
- **Calm and predictable.** Deterministic and synchronous: the computer follows your steps.
- **Accessible to everyone.** If you can type, you can code.
- **Batteries included.** Commands cover the most common use cases.

## Bring your vibes

Paxy is ideal for AI-assisted coding. Modern AI tools stumble on complex syntax, indentation, or hidden imports.  
Paxy avoids all that. One command per line, plain arguments, no boilerplate — the perfect partner for AI.

- **Copy-paste friendly.** Each line is self-contained.
- **Hard to break.** No braces, decorators, or indentation traps.
- **Composable snippets.** Loops, prints, or conditionals can be dropped in like building blocks.
- **Readable by humans _and_ AI.** Simple, declarative steps.
- **No ceremony.** Forget imports and types — just write commands.

## Usage

paxy filename.paxy will compile and run the paxy file.

## Install for development

1. You need Python 3.12, 3.13 or 3.14.

Older Python versions are untested and unlikely to ever be supported.

I use pyenv to use multiple Python versions on my computer: https://github.com/pyenv/pyenv

- Linux: curl -fsSL https://pyenv.run | bash
- Mac: brew install pyenv
- Win: https://github.com/pyenv-win/pyenv-win/blob/master/docs/installation.md

Then add your desired version of Python:

- pyenv install 3.13.7
- pyenv local 3.13.7

2. Create virtual environment:

- python -m venv deps
- source deps/bin/activate

3. Install dependancies:

- pip install -e .[dev]

4. Run tests

- pytest

5. To get Debug information, run with PAXY_DEBUG=1 and it will output information to /tmp/paxy_debug.txt

### Rebuilding documentation

- cd docs
- make html

### Make a package for PyPi

- python -m build

## Commands

When writing paxy files, you can use low-level Python bytecode names (as in the dis module). But we provide high level BASIC Commands:

## Commands

When writing paxy files, you can use low-level Python bytecode names (as in the `dis` module).  
But we provide high-level BASIC-style commands as a friendlier layer.  
These are compiled into Python 3.13 bytecode instructions at build time.

### CMP

`CMP dst lhs cmp rhs`  
Evaluate `lhs <cmp> rhs` (where `<cmp>` is `==`, `!=`, `<`, `<=`, `>`, `>=`) and store the boolean result in `dst`.

### DEC

`DEC x`  
Decrement a variable: `x = x - 1`.

### GOS

`GOS dst fn [args...]`  
Call function `fn` with arguments and store the return value in `dst`.

### IGL

`IGL name [elem1 elem2 ...]`  
Create a `frozenset` from the given elements. Fast-path: all literals become one constant; otherwise build at runtime.

### IF

`IF lhs cmp rhs label`  
Compare `lhs <cmp> rhs`; if true, jump to `label`.

### IMP

`IMP "module"`  
Import a module by name. Equivalent to `__import__("module")`.

### INC

`INC x`  
Increment a variable: `x = x + 1`.

### IN

`IN dst needle haystack`  
Store boolean result of `needle in haystack` into `dst`.

### INP

`INP x`  
Prompt for input: `x = input()`.

### IS

`IS dst lhs rhs`  
Store boolean result of `lhs is rhs` into `dst`.

### NIS

`NIS dst lhs rhs`  
Store boolean result of `lhs is not rhs` into `dst`.

### LBL

`LBL name`  
Define a jump target.

### LET

`LET name value`  
Assign a value.  
`LET name lhs op rhs` also supports operators: arithmetic, comparison, `is`, `in`, etc.

### MAP

`MAP name "k1" v1 "k2" v2 ...`  
Create a dict with string keys.

### MAD

`MAD m k v`  
Set `m[k] = v`.

### MAL

`MAL m k`  
Delete `m[k]`.

### NIN

`NIN dst needle haystack`  
Store boolean result of `needle not in haystack` into `dst`.

### PAR

`PAR dst1 dst2 expr1 expr2`  
Parallel assignment: `dst1, dst2 = expr1, expr2`.

### PNT

`PNT [value]`  
Print a value (or a blank line).

### RNG … RNE

RNG name start end
...body...
RNE

Loop from start up to (but not including) end, assigning each value to var.

### RET

`RET`  
Return `0`.  
`RET value`  
Return the given value.

### ROW

`ROW name [elem1 elem2 ...]`  
Create a row of data.

### SUB ... SBE

SUB name [params...]
... body ...
SBE

Define a function. Use `RET` within it.

### VEC

`VEC name [elem1 elem2 ...]`  
Create a list.

---

These BASIC commands are lowered into the intermediate representation (`paxy.ir`) and then into Python bytecode. You can always mix them with raw CPython opcode names if you want finer control.

- **VEC** — Create list: `VEC v 1 2 3` → `v = [1,2,3]`.

---

### Command Reference (Cheat Sheet)

| Command | Purpose                                 | Example                                   |
| ------- | --------------------------------------- | ----------------------------------------- |
| **CMP** | Compare values and store boolean result | `CMP r a == b`                            |
| **DEC** | Decrement a variable                    | `DEC x` → `x = x - 1`                     |
| **GOS** | Call function, store result             | `GOS z add x y`                           |
| **IGL** | Create frozenset                        | `IGL s 1 2 3` → `s = frozenset({1,2,3})`  |
| **IF**  | Conditional jump                        | `IF a < b loop_start`                     |
| **IMP** | Import a module                         | `IMP "math"`                              |
| **INC** | Increment a variable                    | `INC x` → `x = x + 1`                     |
| **IN**  | Membership test                         | `IN r x arr` → `r = (x in arr)`           |
| **INP** | Read from stdin                         | `INP name` → `name = input()`             |
| **IS**  | Identity test                           | `IS r a b` → `r = (a is b)`               |
| **NIS** | Negated identity test                   | `NIS r a b` → `r = (a is not b)`          |
| **LBL** | Define a jump target                    | `LBL loop_start`                          |
| **LET** | Assign value or expression              | `LET x 10`, `LET y a + b`                 |
| **MAP** | Create dictionary with string keys      | `MAP m "a" 1 "b" 2` → `m = {"a":1,"b":2}` |
| **MAD** | Insert into dict                        | `MAD m "c" 3` → `m["c"]=3`                |
| **MAL** | Delete from dict                        | `MAL m "a"` → `del m["a"]`                |
| **NIN** | Negated membership test                 | `NIN r x arr` → `r = (x not in arr)`      |
| **PAR** | Parallel assignment                     | `PAR a b x y` → `a, b = x, y`             |
| **PNT** | Print a value (or newline)              | `PNT x`                                   |
| **RNG** | Loop over a range of integers           | `RNG i 1 5 … RNE → for i in 1..4`         |
| **RET** | Return from SUB (default 0 if no value) | `RET y`                                   |
| **ROW** | Create tuple                            | `ROW t 1 2 3` → `t = (1,2,3)`             |
| **SUB** | Define a subroutine                     | `SUB add a b ... RET a+b SBE`             |
| **VEC** | Create list                             | `VEC v 1 2 3` → `v = [1,2,3]`             |
