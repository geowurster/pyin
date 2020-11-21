from pyin.operations.base import BaseOperation


class Cast(BaseOperation):

    """Cast to a builtin type."""

    directives = (
        '%list', '%l',
        '%str', '%s',
        '%int', '%i', '%d',
        '%float', '%f')

    def __call__(self, stream):

        mapping = {
            ('%float',  '%f'): float,
            ('%int',    '%i'): int,
            ('%list',   '%l'): list,
            ('%str',    '%s'): str,
            ('%tuple',  '%t'): tuple,
            ('%dict',   '%d'): dict,
            ('%set',        ): set
        }

        func = mapping[self.directive]

        for item in stream:
            yield func(item)
