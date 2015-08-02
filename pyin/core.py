"""
Core components for pyin
"""


import re
import sys
from types import GeneratorType


__all__ = ['pyin']


if sys.version_info[0] == 2:  # pragma no cover
    string_types = basestring,
else:  # pragma no cover
    string_types = str,


def _importer(string, scope, prefix=''):
    matches = set(re.findall(r"(%s[a-zA-Z_][a-zA-Z0-9_]*)\.?" % prefix, string))
    for name in matches:
        try:
            scope[name] = __import__(name)
            _importer(string, scope, prefix='{}.'.format(name))
        except ImportError:
            pass


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
    iterator : hasattr('__iter__')
        An iterator producing one object to be evaluated per iteration.
    var : str, optional
        Expressions reference this variable to access objects from `iterator`
        during processing.
    """

    if isinstance(expressions, string_types):
        expressions = expressions,

    blacklist = ('eval', 'compile', 'exec', 'execfile', 'builtin', 'builtins',
                 '__builtin__', '__builtins__', 'globals', 'locals', '__import__',
                 '_importer', 'map')

    global_scope = {
        k: v for k, v in globals().items() if k not in ('builtins', '__builtins__')}
    global_scope.update(__builtins__={
        k: v for k, v in globals()['__builtins__'].items() if k not in blacklist})
    global_scope.update(builtins=global_scope['__builtins__'])

    # In Python3 map is a generator and not expanded but we can probably
    # safely assume that pyin users aren't doing anything tooooo crazy
    # with map so we just force it to be a list
    local_scope = {}
    for expr in expressions:
        _importer(expr, local_scope)

    for idx, obj in enumerate(iterable):

        for expr in expressions:

            local_scope.update(**{'idx': idx, var: obj})
            result = eval(expr, global_scope, local_scope)

            # Got a generator.  Expand and continue.
            if isinstance(result, GeneratorType):
                obj = list(result)

            # Result is some object.  Pass it back in under `var`.
            elif not isinstance(result, bool):
                obj = result

            # Result is True/False.  Only continue if True.
            # Have to explicitly let string_types through for ''
            # which would otherwise be ignored.
            elif isinstance(result, string_types) or result:
                continue

            # Got something else?  Halt processing for this obj.
            else:
                obj = None
                break

        # Have to explicitly let string_types through for ''
        # which would otherwise be ignored.
        if isinstance(obj, string_types) or obj:
            yield obj
