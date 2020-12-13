import inspect
import sys

from pyin import _compat
from pyin.exceptions import EvaluateError
from pyin.expressions import _compile_wrapper
from pyin.operations.base import BaseOperation


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

                        {cname}: {error}
                """.format(
                    expr=self.directive, cname=e.__class__.__name__, error=e))
                _compat.reraise(
                    EvaluateError,
                    EvaluateError(msg),
                    sys.exc_info()[2])
