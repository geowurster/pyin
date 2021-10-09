"""Base classes."""


import abc

from pyin.exceptions import InvalidDirective


class BaseOperation(object):

    """An operation receives a stream of data and applies a transformation
    to each item. Each operation defines a ``directives`` class attribute
    indicating which commands can be used to deploy the operation. Additional
    required positional arguments and their types can be defined in the
    ``kwargs`` class attribute.

    For example, this operation would invoke functions from the ``operator``
    module against the stream:

        from collections import OrderedDict
        import operator

        class Operator(BaseOperation):

            directives = ('%op', '%operator')
            kwargs = OrderedDict([
                ('operation', str),
                ('value', float)
            ])

            def __init__(self, directive, operation, value, **kwargs):
                super(Operator, self).__init__(directive, **kwargs)
                self.operation = getattr(operator, operation)
                self.value = float(value)

            def __call__(self, stream):
                for item in stream:
                    yield self.operation(item, self.value)

    which can be invoked as:

        $ pyin --gen 'range(3)' %op add 10
        10.0
        11.0
        12.0
    """

    __metaclass__ = abc.ABCMeta

    kwargs = {}
    directives = ()

    def __init__(self, directive, variable, global_scope):

        """
        Parameters
        ==========
        directive : str
        variable : str
        global_scope : dict
        """

        self.directive = directive
        self.variable = variable
        self.global_scope = global_scope

    @classmethod
    def cli_help(cls, directive):

        """Produce a formatted string appropriate for use in the CLI's
        ``$ pyin help <directive>`` command. Text is expected to be formatted
        like a docstring. Useful for dynamically forming help text on classes
        that implement several directives.

        The output of this method is mostly displayed as-is aside from being
        indented slightly.

        This pattern may make formatting and indentation a bit easier.

            @classmethod
            def cli_help(cls, directive):

                '''Write as a normal docstring.'''

                # Let Python do some of the work
                return __doc__
        """

        return cls.__doc__ or "No docstring for directive: {}".format(directive)

    @abc.abstractmethod
    def __call__(self, stream):

        """Execute the operation. The entire ``stream`` is provided in order
        to let operations leverage potential speedups that are only possible
        if the ``stream`` can be accessed.

        Parameters
        ==========
        stream : iterable
            Make no assumptions about this object other than it can be
            iterated over.

        Yields
        ======
        object
            Transformed objects.
        """

    def raise_invalid_directive(self):
        raise InvalidDirective(
            "operation {} has not fully implemented directive: {}".format(
                self.__class__.__name__, self.directive))
