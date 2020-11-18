"""Base classes."""


import abc


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
