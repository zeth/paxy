# paxy/basic/print.py

from typing import Any
from paxy.basic.base import BasicOperation


class Print(BasicOperation):
    def make_ops(self, op_arg: Any):
        # 3.13 call sequence: LOAD_NAME 'print' ; PUSH_NULL ; [args] ; CALL n ; POP_TOP
        self.add_op("LOAD_NAME", "print")
        self.add_op("PUSH_NULL")
        if op_arg is None:
            self.add_op("CALL", 0)
        else:
            self.add_op("LOAD_CONST", op_arg)
            self.add_op("CALL", 1)
        self.add_op("POP_TOP")