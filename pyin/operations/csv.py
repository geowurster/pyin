import csv
import itertools as it

from pyin import _compat
from pyin.operations.base import BaseOperation


class CSV(BaseOperation):

    """Reads and writes CSV data. If the first line is a string then it is
    assumed data should be written, and otherwise it is assumed data should
    be written.

    Use ``%csv`` to route the stream through :obj:`csv.reader` and
    :obj:`csv.writer`, and ``%csvd`` for :obj:`csv.DictReader` and
    :obj:`csv.DictWriter`. The former works for files without a header
    and the latter with a header.
    """

    directives = ('%csv', '%csvd')

    @classmethod
    def cli_help(cls, directive):

        """Read or write CSV data.

        Use '%csv' for files without a header, and '%csvd' for files with a
        header. Note that the latter uses Python's 'csv.DictReader/Writer()'
        classes.
        """

    def __call__(self, stream):

        first = next(stream)
        stream = it.chain([first], stream)

        mapping = {
            (_compat.string_types, '%csv'): csv.reader,
            ((list, tuple), '%csv'): csv.writer,
            (_compat.string_types, '%csvd'): csv.DictReader,
            (dict, '%csvd'): csv.DictWriter
        }

        for (types, directive), cls in mapping.items():
            if isinstance(first, types) and directive == self.directive:
                break
        else:
            raise ValueError(
                "first object in stream is {type} but directive {directive}"
                " does not know what to do".format(
                    type=type(first), directive=self.directive))

        class FakeFile(object):

            """The ``csv.*writer*`` classes expect to write to a file-like
            object, but we mostly want to use these objects as a way to
            serialize data while we control where it ultimately ends up.

            This class makes it posible to intercept the data with a bit of
            internal state management.
            """

            def __init__(self):
                self.cache = None

            def write(self, str):
                self.cache = str

        # Reading data
        if cls in (csv.reader, csv.DictReader):
            for item in cls(stream):
                yield item

        # Writing with 'csv.writer()'
        elif cls is csv.writer:
            ff = FakeFile()
            writer = csv.writer(ff)
            for item in stream:
                writer.writerow(item)
                yield ff.cache

        # Writing with 'csv.DictWriter()'
        elif cls is csv.DictWriter:
            ff = FakeFile()
            writer = csv.DictWriter(ff, fieldnames=list(first))
            writer.writeheader()
            yield ff.cache
            for item in stream:
                writer.writerow(item)
                yield ff.cache

        else:
            raise RuntimeError("a CSV directive does not know what to do")
