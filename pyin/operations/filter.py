from collections import OrderedDict
import itertools as it

from pyin.operations.eval import Eval


class Filter(Eval):

    """Filter items against an expression."""

    directives = (
        '%filter', '%filt',
        '%filterfalse', '%ff')
    kwargs = OrderedDict([('expr', str)])

    @classmethod
    def cli_help(cls, directive):

        if directive in ('%filter', '%filt'):
            return """
            Only keep items in the stream where the expression evaluates
            as 'True'.
            """
        elif directive in ('%filterfalse', '%ff'):
            return """
            Drop items from the stream where the expression evaluates as
            'False'.
            """
        else:
            raise RuntimeError("Unexpected directive: {}".format(directive))

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

        if self.directive in ('%filterfalse', '%ff'):
            selection = (not s for s in selection)

        return it.compress(stream, selection)
