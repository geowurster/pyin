"""
Core components for pyin
"""


from __future__ import division, print_function

from collections import Counter
import functools
import itertools as it
import operator as op
import re
import sys

from pyin import _compat
from pyin.base import BaseOperation
from pyin.exceptions import CompileError


__all__ = ['compile', 'generate', 'importer', 'evaluate']


_DEFAULT_VARIABLE = 'i'
_IMPORTER_REGEX = re.compile(r"([a-zA-Z_.][a-zA-Z0-9_.]*)")


# This gets overloaded later
_builtin_compile = compile
def _compile_wrapper(code, mode='eval'):

    """Wraps the builtin ``compile()`` and translates ``SyntaxError``, which
    is surprisingly difficult to catch, to a more appropriate exception.

    Parameters
    ==========
    code : str
        Code snippet to compile.
    mode : str
        Tells ``compile()`` to compile code in this mode.

    Raises
    ======
    CompileError
        If ``code`` could not be compiled.

    Returns
    =======
    code
        See builtin ``compile()``.
    """

    try:
        return _builtin_compile(
            code,
            '<string>',
            mode,
            division.compiler_flag | print_function.compiler_flag)

    # Trying to catch with 'except SyntaxError as e' just leads to an
    # undefined variable 'e'.
    except SyntaxError:
        _, exc_value, exc_traceback = sys.exc_info()
        _compat.reraise(
            CompileError,
            CompileError.from_syntax_error(exc_value),
            exc_traceback)


def _normalize_expressions(f):

    """Decorator for ensuring a single expression or sequence of multiple
    expressions can be given.
    """

    @functools.wraps(f)
    def inner(expressions, *args, **kwargs):
        if isinstance(expressions, (_compat.string_types, BaseOperation)):
            expressions = expressions,

        strings = [isinstance(i, _compat.string_types) for i in expressions]
        if any(strings) and not all(strings):
            raise TypeError(
                "found a mix of string expressions and operation classes"
                " - input must be homogeneous")

        return f(expressions, *args, **kwargs)

    return inner


@_normalize_expressions
def compile(expressions, variable=_DEFAULT_VARIABLE, scope=None):

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

    # Avoid a circular import
    from pyin import operations

    # Parse expressions and construct a pipeline
    out = []
    expressions = list(expressions)
    while expressions:

        directive = expressions.pop(0)

        # String is a token that requires special processing
        if directive in operations._DIRECTIVE_TO_CLASS:
            cls = operations._DIRECTIVE_TO_CLASS[directive]

        elif directive.startswith(operations._DIRECTIVE_CHARACTER):
            raise CompileError("unrecognized directive: {}".format(directive))

        # String is an expression that can be passed to eval.
        else:
            cls = operations.Eval

        kwargs = {
            name: cast(expressions.pop(0))
            for name, cast in cls.kwargs.items()}

        out.append(cls(
            directive=directive,
            variable=variable,
            global_scope=scope,
            **kwargs))

    return tuple(out)


def default_scope():

    """Default global scope for expression evaluation."""

    return {
        'Counter': Counter,
        'filter': _compat.filter,
        'it': it,
        'itertools': it,
        'map': _compat.map,
        'op': op,
        'operator': op,
        'range': _compat.range,
        'reduce': functools.reduce
    }


@_normalize_expressions
def importer(expressions, scope=None):

    """Parse expressions and import modules into a single scope.

    Parameters
    ----------
    expressions : str or sequence
        Single expression or sequence of expressions.

    Returns
    -------
    OrderedDict
        Mapping between expressions and scopes.
    """

    scope = scope or {}

    # Find all potential modules to try and import
    all_matches = set(it.chain.from_iterable(
        re.findall(_IMPORTER_REGEX, expr) for expr in expressions))

    for match in all_matches:

        split = match.split('.', 1)

        # Like: json.loads()
        if len(split) == 1:
            module = split[0]
            other = []

        # Like: os.path.join()
        elif len(split) == 2:
            module, other = split
            other = [other]

        # Shouldn't hit this
        else:
            raise ImportError("Error importing from: {}".format(match))

        # Are you trying to figure out why relative imports don't work?
        # If so, the issue is probably `m.split()` producing ['', 'name']
        # instead of ['.name']. `__import__('.name')__` doesn't appear
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
def evaluate(expressions, stream, variable=_DEFAULT_VARIABLE, scope=None):

    """Evaluate a sequence of expressions against a stream.

    Parameters
    ----------
    expressions : sequence
        Of strings.
    stream : sequence
        If stuff to process.
    variable : str
        Store data in this variable name in the local scope.
    scope : dict or None
        Import objects referenced in expressions into this scope. Later used
        as the global scope when evaluating expressions.

    Yields
    ------
    object
    """

    scope = scope or default_scope()

    # Can only auto-import when input expressions are strings
    strings = [isinstance(i, _compat.string_types) for i in expressions]
    if all(strings):
        scope = importer(expressions, scope)

    expressions = compile(expressions, variable=variable, scope=scope)

    for func in expressions:
        stream = func(stream)

    for item in stream:
        yield item


def generate(expression):

    """Evaluate an expression in a mode more limited than ``evaluate()`` where
    its output is returned.

    Parameters
    ==========
    expression : str or pyin.BaseExpression
        Expression to evaluate.

    Returns
    =======
    object
        Evaluated expression.
    """

    stream = evaluate(
        [expression],
        [object],     # Need something to iterate over
        variable='_'  # Obfuscate the scope a bit
    )

    return next(stream)
