import csv
import itertools as it

from pyin import _compat
from pyin.operations.base import BaseOperation


class CSV(BaseOperation):

    directives = ('%csv', '%csvd')

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
            def __init__(self):
                self.cache = None
            def write(self, str):
                self.cache = str

        if cls is csv.reader:
            for item in csv.reader(stream):
                yield item

        elif cls is csv.DictReader:
            for record in csv.DictReader(stream):
                yield record

        elif cls is csv.writer:
            ff = FakeFile()
            writer = csv.writer(ff)
            for item in stream:
                writer.writerow(item)
                yield ff.cache

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
