import functools
import itertools
import operator
import re

from . import _compat, operations


__all__ = ['importer', 'compile', 'evaluate']


def _normalize_expressions(f):

    @functools.wraps(f)
    def inner(expressions, *args, **kwargs):
        if isinstance(expressions, _compat.string_types):
            expressions = expressions,
        return f(expressions, *args, **kwargs)

    return inner


@_normalize_expressions
def importer(expressions, scope=None):

    """Parse expressions and import modules into a single scope.

    Parameters
    ----------
    expressions : str
        Sequence of expressions.
    scope : dict or None, optional
        Existing local scope into which imports will be propogated.

    Returns
    -------
    dict
        Modified ``scope``.
    """

    scope = scope or {}

    for expr in expressions:
        matches = set(re.findall(r"([a-zA-Z_.][a-zA-Z0-9_.]*)", expr))
        for m in matches:

            split = m.split('.', 1)

            # Like: json.loads(line)
            if len(split) == 1:
                module = split[0]
                other = []
            # Like: tests.module.upper(line)
            elif len(split) == 2:
                module, other = split
                other = [other]
            # Shouldn't hit this
            else:  # pragma no cover
                raise ImportError("Error importing from: {}".format(m))

            # Are you trying to figure out why relative imports don't work?
            # If so, the issue is probably `m.split()` producing ['', 'name']
            # instead of ['.name'].  `__import__('.name')__` doesn't appear
            # to work though, so good luck!
            if not module:
                continue

            try:
                scope[module] = __import__(
                    module,
                    fromlist=list(map(str, other)),
                    level=0)
            except ImportError:
                pass

    return scope


@_normalize_expressions
def compile(expressions):

    """Parse expressions and compile into a sequence of operations.

    Parameters
    ----------
    expressions : sequence
        Of string expressions and directives.

    Returns
    ------
    tuple
        Of :py:class`BaseOperation` subclassers.
    """

    # Expose these modules in the scope by default.  Will be overwritten by
    # imports.
    global_scope = {
        'it': itertools,
        'op': operator,
        'reduce': functools.reduce}
    global_scope = importer(expressions, global_scope)

    # Parse expressions and construct a pipeline
    out = []
    expressions = list(expressions)
    while expressions:
        token = expressions.pop(0)

        # String is a token that requires special processing
        if token in operations._TOKEN_CLASS:
            cls = operations._TOKEN_CLASS[token]

        # String is an expression that can be passed to eval.
        else:
            cls = operations.Eval

        kwargs = {
            name: cast(expressions.pop(0))
            for name, cast in cls.kwargs.items()}
        out.append(cls(
            token=token,
            global_scope=global_scope,
            **kwargs))

    return tuple(out)


@_normalize_expressions
def evaluate(expressions, stream):

    """Evaluate a sequence of expressions against a stream.

    Parameters
    ----------
    expressions : sequence
        Of strings.
    stream : sequence
        If stuff to process.

    Yields
    ------
    object
    """

    steps = compile(expressions)

    for func in steps:
        stream = func(stream)

    for item in stream:
        yield item
