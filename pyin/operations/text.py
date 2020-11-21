"""Common text processing operations."""


from collections import OrderedDict
import operator as op

from pyin._compat import map
from pyin.operations import _DIRECTIVE_CHARACTER
from pyin.operations.base import BaseOperation


class Strip(BaseOperation):

    """Strip whitespace."""

    directives = ('%strip',)
    _method = 'strip'

    def __call__(self, stream):
        return map(op.methodcaller(self._method), stream)


class LStrip(Strip):

    """Strip leading whitespace."""

    directives = ('%lstrip',)
    _method = 'lstrip'


class RStrip(Strip):

    """Strip trailing whitespace."""

    directives = ('%rstrip',)
    _method = 'rstrip'


class StripC(Strip):

    """Strip non-whitespace characters."""

    directives = ('%stripc',)
    kwargs = OrderedDict([('characters', str)])
    _method = 'strip'

    def __init__(self, directive, variable, global_scope, characters):
        super(StripC, self).__init__(directive, variable, global_scope)
        self.characters = characters

    def __call__(self, stream):
        return map(op.methodcaller(self._method, self.characters), stream)


class LStripC(LStrip):

    """Strip leading non-whitespace characters."""

    directives = ('%lstripc',)


class RStripC(RStrip):

    """Strip trailing non-whitespace characters."""

    directives = ('%rstripc',)


class StrMethod(BaseOperation):

    """Split text on whitespace."""

    directives = (
        '%split',
        '%upper',
        '%lower')

    def __call__(self, stream):
        method = self.directive.lstrip(_DIRECTIVE_CHARACTER)
        return map(op.methodcaller(method), stream)
