from pyin.operations.base import BaseOperation


class Cast(BaseOperation):

    """Cast to a builtin type."""

    directives = ('%list', '%l')

    def __call__(self, stream):

        mapping = {
            ('%list', '%l'): list
        }

        func = mapping[self.directive]

        for item in stream:
            yield func(item)
