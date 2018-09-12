"""High level stream transformations."""


import __future__

import abc
from collections import OrderedDict
import inspect
import itertools as it
import json

from ._compat import filter, string_types


_TOKEN_CLASS = {}


class BaseOperation(object):

    __metaclass__ = abc.ABCMeta

    kwargs = {}
    tokens = ()

    def __init__(self, token, global_scope):
        self.token = token
        self.global_scope = global_scope

    @abc.abstractmethod
    def __call__(self, stream):
        """"""


class Eval(BaseOperation):

    def __call__(self, stream):
        expression = compile(
            self.token, '<string>', 'eval', __future__.division.compiler_flag)
        global_scope = self.global_scope
        local_scope = {}
        for item in stream:
            local_scope['line'] = item
            yield eval(expression, global_scope, local_scope)


class Accumulate(BaseOperation):

    tokens = ('%accumulate', '%acc')

    def __call__(self, stream):
        yield tuple(stream)


class Filter(BaseOperation):

    tokens = '%filter',
    kwargs = OrderedDict([('filtexpr', str)])
    filterfunc = filter

    def __init__(self, filtexpr, **kwargs):
        self.filtexpr = filtexpr
        super(Filter, self).__init__(**kwargs)

    def __call__(self, stream):
        expression = compile(
            self.filtexpr, '<string>', 'eval',
            __future__.division.compiler_flag)
        return self.filterfunc(
            lambda x: eval(
                expression, self.global_scope, {'line': x, 'stream': stream}),
            stream)


class JSON(BaseOperation):

    """Serialize or deserialize JSON.  If the first item in the stream is a
    string with a leading '{' or '[', then this operation deserializes.  If
    the first item is a 'dict', 'list', or 'tuple', then this operation
    serializes.

    For example, given an input array serialized as JSON, append a value to it
    and serialize.

        $ pyin --gen '[0, 1]' %json "line + [2]" %json
        [0, 1, 2]
    """

    tokens = '%json',

    def __call__(self, stream):
        first = next(stream)
        stream = it.chain([first], stream)
        if isinstance(first, string_types):
            func = json.loads
        else:
            func = json.dumps
        return map(func, stream)


for _cls in filter(inspect.isclass, locals().copy().values()):
    if _cls != BaseOperation and issubclass(_cls, BaseOperation):
        for _tkn in _cls.tokens:
            _TOKEN_CLASS[_tkn] = _cls
