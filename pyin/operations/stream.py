from collections import OrderedDict
import itertools as it

from pyin.operations.eval import Eval


class Stream(Eval):

    """Evaluate an expression against the actual ``stream`` object."""

    directives = ('%stream',)
    kwargs = OrderedDict([('expr', str)])

    def __init__(self, directive, variable, global_scope, expr):

        """
        Parameters
        ==========
        expr : str
            Expression to evaluate. The stream object can be found in the
            ``stream`` variable.
        variable : str
            Exists to fulfill the API requirements but is otherwise ignored.
        """
        super(Stream, self).__init__(
            expr, variable='stream', global_scope=global_scope)
        self.directive = directive

    def __call__(self, stream):
        stream = super(Stream, self).__call__([stream])
        return next(stream)
