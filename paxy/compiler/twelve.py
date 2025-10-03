# paxy/compiler/twelve.py
from typing import Union
from bytecode import Bytecode, Instr, Label
from types import CodeType
import os, sys

CallableLoads = {"LOAD_GLOBAL", "LOAD_NAME", "LOAD_FAST", "LOAD_ATTR", "LOAD_DEREF"}


def _prev_instr_idx(seq: list[Union[Instr, Label, object]], start: int) -> int | None:
    j = start - 1
    while j >= 0:
        if isinstance(seq[j], Instr):
            return j
        j -= 1
    return None


def _next_instr_idx(seq: list[Union[Instr, Label, object]], start: int) -> int | None:
    j = start + 1
    while j < len(seq):
        if isinstance(seq[j], Instr):
            return j
        j += 1
    return None


def normalize_push_null_for_calls_312_seq(
    seq: list[Union[Instr, Label, object]],
) -> list[Union[Instr, Label, object]]:
    """
    For Python 3.12, canonicalize every CALL site to:

        ..., PUSH_NULL, <callable>, <arg1>.. <argN>, CALL n

    Also neutralize LOAD_GLOBAL's with-null flag on the callable and
    avoid touching unrelated PUSH_NULLs (especially when lineno=None).
    """
    if sys.version_info >= (3, 13):
        return list(seq)

    s = list(seq)
    i = 0
    while i < len(s):
        ins = s[i]
        if not isinstance(ins, Instr) or ins.name != "CALL":
            i += 1
            continue

        # 1) How many positional args?
        try:
            nargs = int(ins.arg or 0)
        except Exception:
            nargs = 0

        # 2) Backtrack over exactly 'nargs' argument pushes (skip labels & PUSH_NULL)
        cursor = i
        remaining = nargs
        while remaining:
            cursor = _prev_instr_idx(s, cursor)
            if cursor is None:
                break
            if isinstance(s[cursor], Instr) and s[cursor].name == "PUSH_NULL":
                # not an argument
                continue
            remaining -= 1
        if cursor is None or remaining:
            i += 1
            continue  # couldn't robustly locate args

        # 3) Find the callable: previous non-label, non-PUSH_NULL instruction
        callable_ix = _prev_instr_idx(s, cursor)
        while (
            callable_ix is not None
            and isinstance(s[callable_ix], Instr)
            and s[callable_ix].name == "PUSH_NULL"
        ):
            callable_ix = _prev_instr_idx(s, callable_ix)
        if callable_ix is None:
            i += 1
            continue

        callable_ins: Instr = s[callable_ix]  # type: ignore[assignment]

        # 3a) If it's LOAD_GLOBAL with (True, name), flip the flag to False
        if (
            callable_ins.name == "LOAD_GLOBAL"
            and isinstance(callable_ins.arg, tuple)
            and len(callable_ins.arg) == 2
            and isinstance(callable_ins.arg[0], bool)
            and callable_ins.arg[0] is True
        ):
            name = callable_ins.arg[1]
            callable_ins.arg = (False, name)

        # 3b) Remove PUSH_NULLs strictly between callable and CALL (those are always wrong)
        j = callable_ix + 1
        while j < i:
            if isinstance(s[j], Instr) and s[j].name == "PUSH_NULL":
                del s[j]
                if j < i:
                    i -= 1
                continue
            j += 1

        # 4) Ensure there is exactly one PUSH_NULL immediately before the callable.
        call_line = getattr(ins, "lineno", None)

        # Is there already one immediately before?
        has_immediate_null = (
            callable_ix - 1 >= 0
            and isinstance(s[callable_ix - 1], Instr)
            and s[callable_ix - 1].name == "PUSH_NULL"
        )

        if call_line is not None:
            # We can safely use same-line cleanup
            same_line_nulls = [
                j
                for j in range(i)  # strictly before CALL
                if isinstance(s[j], Instr)
                and s[j].name == "PUSH_NULL"
                and getattr(s[j], "lineno", None) == call_line
            ]

            if same_line_nulls:
                keep = same_line_nulls[-1]
                # Drop all other same-line NULLs
                for extra in reversed(same_line_nulls[:-1]):
                    del s[extra]
                    if extra < i:
                        i -= 1
                    if extra < callable_ix:
                        callable_ix -= 1

                # Move the kept one to sit right before the callable
                if keep != callable_ix - 1:
                    node = s.pop(keep)
                    if keep < i:
                        i -= 1
                    if keep < callable_ix:
                        callable_ix -= 1
                    insert_at = max(callable_ix, 0)
                    s.insert(insert_at, node)
                    if insert_at <= i:
                        i += 1
                    callable_ix += 1  # callable shifted right
        else:
            # No reliable line info: be conservative.
            # Only insert a NULL if there isn't an immediate one already.
            if not has_immediate_null:
                ln = getattr(callable_ins, "lineno", None)
                s.insert(callable_ix, Instr("PUSH_NULL", lineno=ln))
                if callable_ix <= i:
                    i += 1
                callable_ix += 1

        # Final belt-and-braces: if there’s still no immediate NULL, insert one now.
        has_immediate_null = (
            callable_ix - 1 >= 0
            and isinstance(s[callable_ix - 1], Instr)
            and s[callable_ix - 1].name == "PUSH_NULL"
        )
        if not has_immediate_null:
            ln = getattr(callable_ins, "lineno", None) or getattr(ins, "lineno", None)
            s.insert(callable_ix, Instr("PUSH_NULL", lineno=ln))
            if callable_ix <= i:
                i += 1
            callable_ix += 1

        i += 1

    return s


def try_func_to_code_with_endfor_fix(bc_func: Bytecode) -> CodeType:
    """
    Compile a function bytecode. If stacksize computation fails (3.12 edge case
    with END_FOR/POP_TOP), retry after removing POP_TOP that immediately follows END_FOR.
    """
    try:
        return bc_func.to_code()
    except RuntimeError as e:
        msg = str(e)
        if "stacksize" not in msg:
            raise
        # Heuristic: in some 3.12 builds, END_FOR already balances stack;
        # a trailing POP_TOP causes the negative pre-delta.
        instrs = list(bc_func)
        fixed = []
        i = 0
        removed = 0
        while i < len(instrs):
            cur = instrs[i]
            if (
                isinstance(cur, Instr)
                and cur.name == "END_FOR"
                and i + 1 < len(instrs)
                and isinstance(instrs[i + 1], Instr)
                and instrs[i + 1].name == "POP_TOP"
            ):
                fixed.append(cur)  # keep END_FOR
                # skip the POP_TOP
                i += 2
                removed += 1
                continue
            fixed.append(cur)
            i += 1

        if removed == 0:
            # Nothing to fix; re-raise original error
            raise

        bc_func[:] = fixed  # mutate in place

        if os.environ.get("PAXY_DEBUG"):
            print(
                "== FUNC POP_TOP-FIX APPLIED == (removed",
                removed,
                "POP_TOP after END_FOR)",
            )

        # Try again; if it still fails, let the error bubble.
        return bc_func.to_code()


def poptop_for_twelve(bc: Bytecode) -> CodeType:
    """
    Compile module bytecode. If 3.12 stacksize computation fails because an
    END_FOR is immediately followed by POP_TOP, drop that POP_TOP and retry.
    """
    if sys.version_info >= (3, 13):
        return bc.to_code()
    try:
        return bc.to_code()
    except RuntimeError as e:
        if "stacksize" not in str(e):
            raise

        instrs = list(bc)
        fixed = []
        i = 0
        removed = 0
        while i < len(instrs):
            cur = instrs[i]
            if (
                isinstance(cur, Instr)
                and cur.name == "END_FOR"
                and i + 1 < len(instrs)
                and isinstance(instrs[i + 1], Instr)
                and instrs[i + 1].name == "POP_TOP"
            ):
                fixed.append(cur)  # keep END_FOR
                i += 2  # skip POP_TOP
                removed += 1
                continue
            fixed.append(cur)
            i += 1

        if removed == 0:
            # Nothing to fix -> original error
            raise

        bc[:] = fixed
        if os.environ.get("PAXY_DEBUG"):
            print("== MODULE POP_TOP-FIX APPLIED ==", "(removed", removed, "POP_TOP)")

        return bc.to_code()
