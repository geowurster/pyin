from collections import OrderedDict
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


class Try(BaseOperation):

    """%try expr exception except_expr"""

    directives = ('%try',)
    kwargs = OrderedDict([
        ('expr', str),
        ('exception', str),
        ('except_expr', str)
    ])

    def __init__(
            self, directive, variable, global_scope,
            expr, exception, except_expr):

        super(Try, self).__init__(directive, variable, global_scope)

        self.expr = expr
        self.compiled_expr = _compile_wrapper(self.expr, mode='eval')

        # Go get the exception class. Make sure the discovered object is
        # an uninstantiated class.
        self.exception = exception
        self.exc = eval(self.exception, self.global_scope, {})
        if not inspect.isclass(self.exc):
            raise TypeError("need a class not: {!r}".format(self.exception))

        self.except_expr = except_expr
        if self.except_expr == 'pass':
            self.compiled_except_expr = None
        else:
            self.compiled_except_expr = _compile_wrapper(
                self.except_expr, mode='eval')

    def __call__(self, stream):

        # Attribute lookup is not free
        expr = self.compiled_expr
        exc = self.exc
        except_expr = self.compiled_except_expr
        variable = self.variable
        global_scope = self.global_scope

        for item in stream:
            try:
                yield eval(expr, global_scope, {variable: item})
            except exc as e:
                if except_expr is None:
                    pass
                else:
                    try:
                        yield eval(
                            except_expr, global_scope, {variable: item, 'e': e})
                    except Exception as e:
                        msg = inspect.cleandoc("""
                            failed to evaluate expression: {expr}

                                {cname}: {error}
                        """.format(
                            expr=self.directive,
                            cname=e.__class__.__name__,
                            error=e))
                        _compat.reraise(
                            EvaluateError,
                            EvaluateError(msg),
                            sys.exc_info()[2])
