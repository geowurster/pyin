import itertools as it
import json

from pyin import _compat
from pyin.operations.base import BaseOperation


class JSON(BaseOperation):

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
