# paxy/basic/let.py

from typing import Any, Tuple
from paxy.basic.base import BasicOperation


class Let(BasicOperation):
    """LET <identifier> <literal>  ->  LOAD_CONST <literal>; STORE_NAME <identifier>"""
    def make_ops(self, op_arg: Any):
        if not (isinstance(op_arg, tuple) and len(op_arg) == 2 and isinstance(op_arg[0], str)):
            raise SyntaxError("LET expects (name, value)")
        name, value = op_arg  # type: Tuple[str, Any]
        self.add_op("LOAD_CONST", value)
        self.add_op("STORE_NAME", name)
