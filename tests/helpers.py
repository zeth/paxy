from bytecode.instr import _UNSET as _UNSET_CTOR

UNSET = _UNSET_CTOR()


def as_pairs(instrs):
    return [(str(i.name), i.arg) for i in instrs]
