from collections import OrderedDict

from pyin.operations.eval import Eval


class Stream(Eval):

    """Evaluate an expression against the actual ``stream`` object."""

    directives = ('%stream',)
    kwargs = OrderedDict([('expr', str)])

    @classmethod
    def cli_help(cls, directive):

        """Manipulate the core data stream.

        For example, the stream can be reversed with:

            %stream "list(stream)[::-1]"

        at the cost of reading the entire stream into memory.
        """

        return __doc__

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

        yield next(stream)
