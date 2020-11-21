from collections import OrderedDict
import itertools as it

from pyin.operations.base import BaseOperation


class Flatten(BaseOperation):

    """Flatten nested iterators."""

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
