"""Operations for transforming individual items in a stream."""


from __future__ import division, print_function

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
        super().__init__(*args, **kwargs)
        self.expr = _compile_wrapper(self.directive, mode='eval')

    def __call__(self, stream):

        # Attribute lookup is not free
        expr = self.expr
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


for _cls in filter(inspect.isclass, locals().copy().values()):
    if _cls != BaseOperation and issubclass(_cls, BaseOperation):
        for _d in _cls.directives:
            if not _d.startswith(_DIRECTIVE_CHARACTER):
                raise ImportError(
                    "operation {} has a directive that does not start with"
                    " {}".format(_cls.__name__, _DIRECTIVE_CHARACTER))
            _DIRECTIVE_TO_CLASS[_d] = _cls
del _cls, _d
