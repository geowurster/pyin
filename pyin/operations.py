"""High level stream transformations."""


import __future__

import abc
from collections import OrderedDict
import inspect

from ._compat import filter


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


for _cls in filter(inspect.isclass, locals().copy().values()):
    if _cls != BaseOperation and issubclass(_cls, BaseOperation):
        for _tkn in _cls.tokens:
            _TOKEN_CLASS[_tkn] = _cls
