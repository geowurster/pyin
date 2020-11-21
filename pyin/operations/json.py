import itertools as it

from pyin import _compat
from pyin.operations.base import BaseOperation


class JSON(BaseOperation):

    """Parses JSON when receiving a string and attempts to serialize when
    receiving an appropriate type.

    Note that this mode is determined based on the first line and subsequent
    lines are not checked.
    """

    directives = ('%json',)

    def __call__(self, stream):

        import json

        stream = (i for i in stream)

        first = next(stream)
        stream = it.chain([first], stream)

        allowed_types = tuple(list(_compat.string_types) + [_compat.binary_type])
        if isinstance(first, allowed_types):
            func = json.JSONDecoder().decode
        else:
            func = json.JSONEncoder().encode

        return _compat.map(func, stream)
