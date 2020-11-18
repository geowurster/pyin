"""Operations for transforming individual items in a stream."""


from __future__ import division, print_function

from collections import OrderedDict
import itertools as it
import inspect
import sys

from pyin import _compat
from pyin.base import BaseOperation
from pyin.exceptions import EvaluateError
from pyin.expressions import _compile_wrapper


_DIRECTIVE_TO_CLASS = {}
_DIRECTIVE_CHARACTER = '%'


class Eval(BaseOperation):

    """Evaluate a Python expression to transform an object in the stream."""

    directives = ('%eval',)

    def __init__(self, *args, **kwargs):
        super(Eval, self).__init__(*args, **kwargs)
        self.expr = self.directive
        self.compiled_expr = _compile_wrapper(self.expr, mode='eval')

    def __call__(self, stream):

        # Attribute lookup is not free
        expr = self.compiled_expr
        variable = self.variable
        global_scope = self.global_scope

        for item in stream:
            try:
                yield eval(expr, global_scope, {variable: item})
            except Exception as e:
                msg = inspect.cleandoc("""
                    failed to evaluate expression: {expr}

                        {error}
                """.format(expr=self.directive, error=e))
                _compat.reraise(
                    EvaluateError,
                    EvaluateError(msg),
                    sys.exc_info()[2])


class Filter(Eval):

    """Filter items against an expression."""

    directives = ('%filter', '%filt')
    kwargs = OrderedDict([('expr', str)])

    def __init__(self, directive, variable, global_scope, expr):

        """
        Parameters
        ==========
        expr : str
            Expression to evaluate as true/false.
        """
        super(Filter, self).__init__(expr, variable=variable, global_scope=global_scope)
        self.directive = directive

    def __call__(self, stream):
        stream, selection = it.tee(stream, 2)
        selection = super(Filter, self).__call__(selection)
        return it.compress(stream, selection)


class List(BaseOperation):

    """Call ``list()`` on every item."""

    directives = ('%list',)

    def __call__(self, stream):
        for item in stream:
            yield list(item)


for _cls in filter(inspect.isclass, locals().copy().values()):
    if _cls != BaseOperation and issubclass(_cls, BaseOperation):
        for _d in _cls.directives:
            if not _d.startswith(_DIRECTIVE_CHARACTER):
                raise ImportError(
                    "operation {} has a directive that does not start with"
                    " {}".format(_cls.__name__, _DIRECTIVE_CHARACTER))
            _DIRECTIVE_TO_CLASS[_d] = _cls
del _cls, _d
