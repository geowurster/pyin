from collections import OrderedDict
import itertools as it

from pyin.operations.eval import Eval


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
