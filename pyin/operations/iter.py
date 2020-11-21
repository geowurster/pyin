from collections import OrderedDict
import itertools as it
from types import GeneratorType

from pyin import _compat
from pyin.operations.base import BaseOperation


class Flatten(BaseOperation):

    """Flatten nested iterators into a continuous stream."""

    directives = ('%flatten', '%explode', '%chain')

    def __call__(self, stream):
        return it.chain.from_iterable(stream)


class Accumulate(BaseOperation):

    """Accumulate the entire stream into a single list."""

    directives = ('%accumulate', '%acc')

    def __call__(self, stream):
        yield list(stream)


class Slice(BaseOperation):

    """Slice the stream into chunks of at least N elements stored in a
    ``list``.
    """

    directives = ('%slice',)
    kwargs = OrderedDict([('chunksize', int)])

    def __init__(self, *args, **kwargs):
        self.chunksize = kwargs.pop('chunksize')
        super(Slice, self).__init__(*args, **kwargs)

    def __call__(self, stream):
        stream = (i for i in stream)
        chunksize = self.chunksize
        islice = it.islice
        while True:
            try:
                yield list(islice(stream, chunksize))
            except StopIteration:
                break


class Reverse(BaseOperation):

    """Reverse each item with ``%rev`` and the entire stream with ``%revs``."""

    directives = ('%rev', '%revs')

    def __init__(self, *args, **kwargs):
        super(Reverse, self).__init__(*args, **kwargs)
        self.reverse_by_index = tuple(list(_compat.string_types) + [list, tuple])

    @classmethod
    def cli_help(cls, directive):

        if directive == '%rev':
            return """
            Reverse each item in the stream.
            """
        elif directive == '%revs':
            return """
            Reverse the entire stream.
            """
        else:
            raise RuntimeError("Unrecognized directive: {}".format(directive))

    def reverse(self, item):
        if isinstance(item, self.reverse_by_index):
            return item[::-1]
        elif isinstance(item, GeneratorType):
            return (i for i in reversed(tuple(item)))
        else:
            return reversed(item)

    def __call__(self, stream):

        if self.directive == '%revs':
            for item in self.reverse(stream):
                yield item
        elif self.directive == '%rev':
            for item in _compat.map(self.reverse, stream):
                yield item
        else:
            self.raise_invalid_directive()
