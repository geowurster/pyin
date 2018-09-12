import functools
import itertools
import operator
import os
import re
import traceback
from types import GeneratorType

from . import _compat


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

    if isinstance(expressions, _compat.string_types):
        expressions = [expressions]

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


def pmap(expressions, iterable, var='line'):

    """
    Like `map()` but with `eval()` and multiple Python expressions.
    Expressions can access the current line being processed with a variable
    called `line`.

    It's like being dropped inside of a `for` loop and with the ability to
    create simple `if` statements and variable re-assignment.  This:

        for line in iterable:
            if 'mouse' in line:
                line = line.upper()
            if 'cat' in line:
                yield line

    turns into this:

        expressions = (
            "line.upper() if 'mouse' in var else line",
            "'cat' in var")
        pmap(expressions, iterable, var='line')

    Expressions are Python code that are passed through `eval()`, which is
    given a modified global and local scope to help prevent mishaps by default.
    External modules are automatically imported so don't pass any code to
    `pmap()` that you wouldn't pass to `eval()`.

    Expressions can be used for a limited amount of control flow and filtering
    depending on what comes out of `eval()`.  There are 3 types of objects
    that an expression can return, and in some cases the object stored in `var`
    is changed:

        True : The original object from the `iterator` is passed to the next
               expression for evaluation.  If the last expression produces
               `True` the object is yielded.  Whatever is currently stored
               in `var` remains unchanged.

        False or None: Expression evaluation halts and processing moves on to
                       the next object from `iterator`.

        <object> : Expression results that aren't `True` or `False` are
                   placed inside of the `var` name for subsequent expressions.

    So, use expressions that evaluate as `True` or `False` to filter lines and
    anything else to transform content.

    Consider the following example CSV and expressions using `line` as `var`:

        "field1","field2","field3"
        "l1f1","l1f2","l1f3"
        "l2f1","l2f2","l3f3"
        "l3f1","l3f2","l3f3"
        "l4f1","l4f2","l4f3"
        "l5f1","l5f2","l5f3"

    This expression would only return the first line because it evaluates as
    `True` and the rest evaluate as `False`:

        "'field' in line"

        is the same as:

        for line in iterator:
            if 'field' in line:
                yield line

    To capitalize the second line:

        "line.upper() if 'l2' in line"

        is the same as:

        for line in iterator:
           if 'l2' in line:
               line = line.upper()

    Convert to JSON encoded lists:

        "map(lambda x: x.replace('\"', ''), line.strip().split(','))"

        is the same as (this could be condensed):

        for line in iterator:
            line = line.strip().replace('"', '').strip()
            yield line.split(',')


    Parameters
    ----------
    expressions : str or tuple
        A single Python expression or tuple containing multiple expressions.
        Expressions are Python code that can reference external modules, which
        will automatically be imported.
    iterable : hasattr('__iter__')
        An iterator producing one object to be evaluated per iteration.
    var : str, optional
        Expressions reference this variable to access objects from `iterator`
        during processing.
    """

    if isinstance(expressions, _compat.string_types):
        expressions = expressions,
    else:
        expressions = tuple(expressions)

    global_scope = importer(
        expressions,
        {
            'it': itertools,
            'op': operator,
            'reduce': functools.reduce
        })

    compiled_expressions = []
    for expr in expressions:
        try:
            compiled_expressions.append(compile(expr, '<string>', 'eval'))
        except SyntaxError:
            raise SyntaxError(
                "Could not compile expression:"
                " {expression}{ls}{ls}{traceback}".format(
                    expression=expr,
                    ls=os.linesep,
                    traceback=traceback.format_exc(0)))

    for idx, obj in enumerate(iterable):

        for expr in compiled_expressions:

            result = eval(expr, global_scope, {'idx': idx, var: obj})

            # Got a generator.  Expand and continue.
            if isinstance(result, GeneratorType):
                obj = list(result)

            # Result is some object.  Pass it back in under `var`.
            elif not isinstance(result, bool):
                obj = result

            # Result is True/False.  Only continue if True.
            # Have to explicitly let string_types through for ''
            # which would otherwise be ignored.
            elif isinstance(result, _compat.string_types) or result:
                continue

            # Got something else?  Halt processing for this obj.
            else:
                obj = None
                break

        # Have to explicitly let string_types through for ''
        # which would otherwise be ignored.
        if isinstance(obj, _compat.string_types) or obj:
            yield obj
