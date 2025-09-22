# paxy/basic/input.py

from typing import Any
from paxy.basic.base import BasicOperation


class Input(BasicOperation):
    """INPUT <identifier>  ->  LOAD_NAME 'input'; PUSH_NULL; CALL 0; STORE_NAME <identifier>"""
    def make_ops(self, op_arg: Any):
        if not isinstance(op_arg, str):
            raise SyntaxError("INPUT expects an identifier")
        # 3.13 non-method call dance
        self.add_op("LOAD_NAME", "input")
        self.add_op("PUSH_NULL")
        self.add_op("CALL", 0)
        self.add_op("STORE_NAME", op_arg)
