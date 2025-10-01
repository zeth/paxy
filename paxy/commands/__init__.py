# paxy/basic/__init__.py

from typing import Any
from dis import opmap

from paxy.commands.base import BasicItem
from paxy.commands.core import CORE_COMMANDS


BLOCK_OPS = {"SUB", "SBE", "RNG", "RNE"}


def is_command(op_name: str) -> bool:
    return op_name in CORE_COMMANDS


VALID_COMMANDS = set(opmap) | set(CORE_COMMANDS) | BLOCK_OPS


def is_command_name(op_name: str) -> bool:
    return op_name in VALID_COMMANDS


def command(op_name: str, op_args: list[Any], lineno: int) -> list[BasicItem]:
    cls = CORE_COMMANDS[op_name]
    inst = cls(op_args, lineno)
    return inst.ops
