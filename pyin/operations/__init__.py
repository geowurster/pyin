import importlib

from pyin._compat import map
from pyin.operations.base import BaseOperation


# All directives must start with this character
_DIRECTIVE_CHARACTER = '%'


# Mapping between directives and operation classes. Populated by '_init()'.
_REGISTRY = {}


def _init():

    """Note: This function is called below and immediately deleted.

    Ultimately a mapping between directives and operation classes are
    needed, but operations are complicated. Some subclass others, some
    use others directly, some classes declare different directives for
    different behaviors, etc.

    Rather than attempt to manually maintain imports and manage a mapping,
    this function imports all files in ``pyin/operations`` and discovers
    all operation classes. Placing the logic in this function makes it easier
    to clean up the environment once everything is imported.
    """

    # Meh. Surely there is a better way...

    global _REGISTRY

    modules = (
        "pyin.operations.builtins",
        "pyin.operations.eval",
        "pyin.operations.filter"
    )

    for module in map(importlib.import_module, modules):
        for objname in dir(module):
            obj = getattr(module, objname)
            try:
                should_load = issubclass(obj, BaseOperation)
            except TypeError:
                continue
            if should_load:
                for directive in obj.directives:
                    if directive not in _REGISTRY:
                        _REGISTRY[directive] = obj
                    # Operations can import and use other operations, so it is
                    # possible to discover the same object twice.
                    elif obj is _REGISTRY[directive]:
                        pass
                    else:
                        raise ImportError(
                            "operation classes {new_name} and {old_name} have"
                            " a directive collision: {directive}".format(
                                new_name=obj.__name__,
                                old_name=_REGISTRY[directive].__name__,
                                directive=directive))


_init()
del _init
