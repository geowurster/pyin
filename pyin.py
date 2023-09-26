"""It's like ``sed``, but Python!"""


import abc
import argparse
import builtins
from collections import deque
import csv
import functools
import importlib
import inspect
import itertools as it
import json
import sys
import signal
import operator as op
import os
import re
import traceback
from types import CodeType
from typing import (
    Callable, Iterable, List, Optional, Sequence, TextIO, Tuple, Union)


__all__ = ['eval']


__version__ = '1.0dev'
__author__ = 'Kevin Wurster'
__license__ = '''
New BSD License

Copyright (c) 2015-2023, Kevin D. Wurster
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* The names of pyin its contributors may not be used to endorse or
  promote products derived from this software without specific prior written
  permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


_DEFAULT_VARIABLE = 'i'
_DEFAULT_STREAM_VARIABLE = 'stream'
_IMPORTER_REGEX = re.compile(r"([a-zA-Z_.][a-zA-Z0-9_.]*)")
_DIRECTIVE_REGISTRY = {}


def _normalize_expressions(f: Callable) -> Callable:

    """Ensure functions can receive single or multiple expressions.

    Function's first positional argument must be called ``expressions``.

    :param f:
        Decorated function.
    """

    @functools.wraps(f)
    def inner(expressions, *args, **kwargs):

        if isinstance(expressions, str):
            expressions = (expressions, )
        elif not isinstance(expressions, Sequence):
            raise TypeError(f"not a sequence: {expressions=}")

        return f(tuple(expressions), *args, **kwargs)

    return inner


@_normalize_expressions
def compile(
        expressions: Union[str, Sequence[str]],
        variable: str = _DEFAULT_VARIABLE,
        stream_variable: str = _DEFAULT_STREAM_VARIABLE,
        scope: Union[None, dict] = None
) -> Tuple[CodeType]:

    """Compile expressions to Python :module:`code` objects.

    Python's :func:`eval` compiles expressions before executing, but does not
    cache them. Given that we execute each expression as much as once per
    line, we can achieve a noticeable speedup by pre-compiling the expressions.

    :param expressions:
        Expressions to compile.
    :param stream_variable:
        Instruct operations to use this variable when evaluating Python
        expressions against the entire stream.
    """

    compiled = []

    # Note that 'scope = scope or {}' is different from 'if scope is None'.
    # The latter always creates a new dict if the caller does not pass one,
    # and the latter creates a new dict if the caller passes an empty dict.
    # The former makes it impossible to update an existing empty scope, while
    # the latter does not.
    if scope is None:
        scope = {}

    tokens = list(expressions)
    del expressions

    # Check for empty strings in expressions. A check with 'all(tokens)' may
    # be sufficient, but could be confused by '__bool__()'.
    if not all(len(t) for t in tokens):
        raise SyntaxError(
            f"one or more expression is an empty string:"
            f" {' '.join(map(repr, tokens))}")

    while tokens:

        # Get a directive
        directive = tokens.pop(0)

        # If it is not actually a directive just assume it is a Python
        # expression that should be evaluated. Stick the token back in the
        # queue so that it can be evaluated as an argument - makes the rest
        # of the code simpler.
        if directive[0] != '%':
            tokens.insert(0, directive)
            directive = OpEval.directives[0]

        if directive not in _DIRECTIVE_REGISTRY:
            raise ValueError(f'invalid directive: {directive}')
        cls = _DIRECTIVE_REGISTRY[directive]

        # Operation classes define how many arguments are associated with the
        # directives they service with annotated positional-only arguments.
        # Find them.

        sig = inspect.signature(cls.__init__)
        pos_only = [
            p for p in sig.parameters.values()
            if p.kind == p.POSITIONAL_ONLY
        ]
        pos_only = pos_only[1:]  # First is 'self'

        # Arguments for instantiating argument class
        args = [directive]
        for param in pos_only[1:]:

            # Ran out of CLI arguments but expected more
            if not len(tokens):
                raise ValueError(
                    f"missing argument '{param.name}' for directive:"
                    f" {directive}")

            args.append(param.annotation(tokens.pop(0)))

        kwargs = {
            'variable': variable,
            'scope': scope,
            'stream_variable': stream_variable
        }

        compiled.append(cls(*args, **kwargs))

    return tuple(compiled)


@_normalize_expressions
def importer(
        expressions: Union[str, Sequence[str]],
        scope: dict
) -> dict:

    """Parse expressions and import modules into a single scope.

    All :obj:`ImportError`s are suppressed. It is pretty much impossible to
    know if a given module is expected to be importable, but in the event
    a module really does fail to import, a :obj:`NameError` will be raised at
    runtime when an expression references an object that does not exist.

    :param expressions:
        Look through these expressions and attempt to import anything that
        looks like a reference to a module.
    :param scope:
        Import modules into this scope. For use with Python's :func:`eval`.
    """

    # Find all potential modules to try and import
    all_matches = set(it.chain.from_iterable(
        re.findall(_IMPORTER_REGEX, expr) for expr in expressions))

    for match in all_matches:

        # 'match' could be something like:
        #   json.dumps
        #   collections.OrderedDict.items
        module = match.split('.', 1)[0]

        # Try and limit the number of import attempts, but only when confident.
        if not module or hasattr(builtins, module):
            continue

        try:
            scope[module] = importlib.import_module(module)

        # Failed to import. To be helpful, check and see if the module exists.
        # if it does, the caller is referencing something that cannot be
        # imported, like a class method. Unclear how to trigger this in a test.
        except ImportError:  # pragma no cover
            res = importlib.util.find_spec(module)
            if res is not None:
                raise ImportError(
                    f"attempting to import something that cannot be imported"
                    f" from a module that does exist: {match}"
                )  # pragma no cover

    return scope


@_normalize_expressions
def eval(
        expressions,
        stream,
        variable: str = _DEFAULT_VARIABLE,
        stream_variable: str = _DEFAULT_STREAM_VARIABLE
):

    """Map Python expressions across a stream of data.

    .. warning::

        This function makes heavy use of Python's :func:`eval`, so a Python
        expression evaluated by this function should be one that you are
        comfortable passing to Python's :func:`eval`. Mostly this means that
        only trusted code should be executed, but be sure to read the
        appropriate Python docs.

        One major difference is that the input expressions are examined, and
        any referenced modules are imported dynamically. For example, an
        expression like ``"os.path.exists(line)"`` would cause ``os.path.exists``
        to be imported.

    Expressions can access the current line being processed with a variable
    called `line`. The goal is to emulate being dropped inside a ``for`` loop
    with limited overhead, and maximum access to Python libraries.

    For example, this:

    .. code-block:: python

        for line in iterable:
            if 'mouse' in line:
                line = line.upper()
            if 'cat' in line:
                yield line

    would be expressed as:

    .. code-block:: python

        expressions = (
            "line.upper() if 'mouse' in var else line",
            "'cat' in var")
        pyin.eval(expressions, iterable, var='line')

    Expressions can be used for a limited amount of control flow and filtering
    depending on what comes out of :func:`eval`. There are 3 types of objects
    that an expression can return, and in some cases the object stored in
    ``variable`` is changed:

    * ``True`` - The original object from the ``iterator`` is passed to the
      next expression for evaluation. If the last expression produces `True`
      the object is yielded. Whatever is currently stored in ``variable``
      remains unchanged.
    * ``False`` or ``None`` - Expression evaluation halts and processing moves
      on to the next object from `iterator`.
    * ``object`` - Expression results that aren't `True` or `False` are placed
      inside the ``variable`` name for subsequent expressions.

    So, use expressions that evaluate as ``True`` or ``False`` to filter lines
    and anything else to transform content.

    Consider the following example CSV and expressions using ``line`` as
    ``variable``:

    .. code-blocK::

        "field1","field2","field3"
        "l1f1","l1f2","l1f3"
        "l2f1","l2f2","l3f3"
        "l3f1","l3f2","l3f3"
        "l4f1","l4f2","l4f3"
        "l5f1","l5f2","l5f3"

    This expression:

    .. code-block::

        "'field' in line"

    is equivalent to:

    .. code-block:: python

        for line in iterator:
            if 'field' in line:
                yield line

    and would only return the first line because it evaluates as ``True`` and
    the rest evaluate as ``False``.

    To capitalize the second line the expression:

    .. code-block::

        "line.upper() if 'l2' in line"

    would be equivalent to:

    .. code-block:: python

        for line in iterator:
           if 'l2' in line:
               line = line.upper()

    Convert to JSON encoded lists using this odd expression:

    .. code-block::

        "map(lambda x: x.replace('\"', ''), line.strip().split(','))"

    Equivalent to this Python code:

    .. code-block:: python

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
    variable : str, optional
        Expressions reference this variable to access objects from `iterator`
        during processing.
    stream_variable : str, optional
        Some expressions are evaluated against the stream itself. Place the
        stream in this variable.
    """

    scope = {
        'it': it,
        'op': op,
        'reduce': functools.reduce
    }

    importer(expressions, scope=scope)
    compiled_expressions = compile(
        expressions,
        variable=variable,
        stream_variable=stream_variable,
        scope=scope
    )

    for op_instance in compiled_expressions:
        stream = op_instance(stream)

    yield from stream


###############################################################################
# Operations


def _peek(iterable):

    """Peek at the first item of an iterable.

    :param iterable iterable:
        Get the first item from this iterable.

    :return:
        A ``tuple`` with two elements. The first is the next value in
        ``iterable``, and the second is the reconstructed iterable, but
        likely as a different type.
    """

    iterable = (i for i in iterable)
    first = next(iterable)
    return first, it.chain([first], iterable)


class OpBase(abc.ABC):

    """Base class for defining an operation.

    Subclassers can use positional-only arguments and type annotations in
    ``__init__`` to define arguments associated with the directive and
    their type.
    """

    directives = None

    def __init__(
            self,
            directive: str,
            /,
            variable: str,
            stream_variable: str,
            scope: dict
    ):

        """
        :param str directive:
            The directive actually usd in the expressions. Some operation
            classes can support multiple directives.
        :param str variable:
            Operations executing expressions with Python's ``eval()`` should
            place data in this variable in the scope.
        :param str stream_variable:
            Like ``variable`` but for referencing the full stream of data.
        :param dict scope:
            Operations executing expressions with Python's ``eval(0)`` should
            use this global scope.
        """

        self.directive = directive
        self.variable = variable
        self.stream_variable = stream_variable
        self.scope = scope

        if self.directive not in self.directives:
            raise ValueError(
                f"instantiated '{repr(self)}' with directive"
                f" '{self.directive}' but supports:"
                f" {' '.join(self.directives)}"
            )

    def __init_subclass__(cls, /, directives: Sequence, **kwargs):

        """Register subclass and its directives.

        Also populates ``Operations.directives`` class variable.

        :param str directives:
            Directives supported by this class. Like ``('%upper', '%lower')``.
        :param **kwargs kwargs:
            Additional arguments.
        """

        global _DIRECTIVE_REGISTRY

        # First validate subclass
        sig = inspect.signature(cls.__init__)

        # Positional-only arguments are used to define arguments for a
        # directive.
        pos_only = [
            p for p in sig.parameters.values()
            if p.kind == p.POSITIONAL_ONLY
        ]
        pos_only = pos_only[1:]  # First is 'self'
        if not pos_only:
            raise RuntimeError(
                f"{cls.__name__}.__init__() is malformed and lacks the"
                f" positional-only arguments used for determining directive"
                f" arguments"
            )

        # Positional arguments _must_ be type hinted for casting purposes.
        for param in pos_only:
            if param.annotation == inspect._empty:
                raise RuntimeError(
                    f"argument '{param.name}' for directive"
                    f" '{cls.__name__}.__init__()' must have a type annotation"
                )

        # Register subclasss
        super().__init_subclass__(**kwargs)
        for d in directives:
            if d[0] != '%' or d.count('%') != 1:
                raise RuntimeError(
                    f"directive '{d}' for class '{cls.__name__}' is not"
                    f" prefixed with a single '%'")
            elif d in _DIRECTIVE_REGISTRY:
                raise RuntimeError(
                    f"directive '{d}' conflict:"
                    f" {cls} {_DIRECTIVE_REGISTRY[d]}")

            cls.directives = directives
            _DIRECTIVE_REGISTRY[d] = cls

    def __repr__(self) -> str:

        """Approximate representation of operation instance."""

        return f"<{self.__class__.__name__}({self.directive}, ...)>"

    @abc.abstractmethod
    def __call__(self, stream):

        """Process a stream of data.

        Implementation must:

        1. Treat ``stream`` as an iterable object and be otherwise agnostic
           to its type. Iterating directly as a ``for`` loop, or wrapping
           as a generator via ``(i for i in stream)`` are both appropriate.
        2. Consume all items in ``stream``.
        3. Be a generator or return an iterator.

        :param stream:
            Input data stream. An iterable object.

        :return:
            An iterable object.
        """

        raise NotImplementedError  # pragma no cover


class OpEval(OpBase, directives=('%eval', )):

    """Evaluate a Python expression with :obj:`eval`.

    .. note::

        This operation receives special treatment in :func:`compile`, but its
        subclassers do not. When parsing the input expressions, any expression
        not associated with a directive is assumed to be a generic Python
        expression that should be handled by this class. Users may still use
        the ``%eval`` directive.
    """

    def __init__(self, directive: str, expression: str, /, **kwargs):

        """
        :param expression:
            Python expression.
        """

        super().__init__(directive, **kwargs)

        self.expression = expression
        try:
            self.compiled_expression = builtins.compile(
                self.expression, '<string>', 'eval')
        except SyntaxError as e:
            raise SyntaxError(
                f"expression {repr(self.expression)} contains a syntax error:"
                f" {e.text}"
            )

    def __call__(self, stream: Iterable):

        # Attribute lookup is not free
        expr = self.compiled_expression
        variable = self.variable
        scope = self.scope
        builtins_eval = builtins.eval

        for item in stream:
            yield builtins_eval(expr, scope, {variable: item})


class OpFilter(OpEval, directives=('%filter', '%filterfalse')):

    """Filter data based on a Python expression.

    These are equivalent:

    .. code-block::

        %filter "i > 2"
        %filterfalse "i <= 2"
    """

    def __call__(self, stream: Sequence) -> Sequence:

        stream, selection = it.tee(stream, 2)
        selection = super().__call__(selection)

        if self.directive == '%filterfalse':
            selection = (not s for s in selection)

        return it.compress(stream, selection)


class OpAccumulate(
        OpBase, directives=('%acc', '%accumulate', '%collect')):

    """Accumulate the entire stream into a single object."""

    def __call__(self, stream):
        yield list(stream)


class OpFlatten(OpBase, directives=('%explode', '%flatten', '%chain')):

    """Flatten the stream by one level – like :obj:`itertools.chain`."""

    def __call__(self, stream):
        return it.chain.from_iterable(stream)


class OpJSON(OpBase, directives=('%json', )):

    """Serialize/deserialize JSON data.

    If the input is a string it is assumed to be JSON and deserialized.
    Otherwise, it is serialized.
    """

    def __call__(self, stream: Iterable) -> Iterable:

        first, stream = _peek(stream)

        # 'json.loads/dumps()' both use these objects internally, but create
        # an instance with every call. Presumably this is faster.
        if isinstance(first, str):
            func = json.JSONDecoder().decode
        else:
            func = json.JSONEncoder().encode

        return map(func, stream)


class OpStream(OpEval, directives=('%stream', )):

    """Evaluate an expression on the stream itself.

    Scope provides access to the entire stream via ``stream_variable`` instead
    of individual items from the stream.
    """

    def __init__(self, directive: str, expression: str, /, **kwargs):

        """See parent implementation.

        This operation can only operate on the stream, so it places
        ``stream_variable`` in ``variable``, and sets the former to ``None``
        since it is irrelevant.

        :param str directive:
            See parent implementation.
        :param str expression:
            Evaluate this expression.
        :param **kwargs kwargs:
            For parent ``__init__()`` method.
        """

        super().__init__(directive, expression, **kwargs)
        self.variable = self.stream_variable
        self.stream_variable = None

    def __call__(self, stream):

        # This method can receive any object, but convert it to an iterator
        # to provide consistency before passing to the expression.
        stream = (i for i in stream)

        # Use the parent implementation and a bit of trickery to instead
        # operate on the stream itself.
        return next(super().__call__([stream]))


class OpCSVDict(OpBase, directives=('%csvd', )):

    """Read/write data via ``csv.DictReader()`` and ``csv.DictWriter()``.

    If the input data is text data is parsed with the default
    ``csv.DictReader()`` settings. Otherwise, a header and rows with "quote
    all" enabled are written.
    """

    def __call__(self, stream: Sequence):

        first, stream = _peek(stream)

        # Reading from a CSV
        if isinstance(first, str):
            yield from csv.DictReader(stream)

        # Writing to a CSV
        else:

            # This file-like object doesn't actually write to a file. Since
            # 'csv.DictWriter.write()' just returns values up the chain, just
            # returning from 'FakeFile.write()' is enough to get a line of
            # text to pass down the line.
            class FakeFile:
                def write(self, data):
                    return data

            writer = csv.DictWriter(
                FakeFile(),
                fieldnames=list(first.keys()),
                quoting=csv.QUOTE_ALL,
                lineterminator='',  # pyin itself handles newline characters
            )

            yield writer.writeheader()
            for row in stream:
                yield writer.writerow(row)


class OpReversed(OpBase, directives=('%rev', '%revstream')):

    """Reverse item/stream."""

    def __call__(self, stream: Sequence):

        # Python's 'reversed()' is kind of weird, and seems to only work well
        # when the object is immediately iterated over. So, to be more helpful,
        # we have some very extra special handling here.

        # Reverse each item
        if self.directive in ('%rev', '%reversed'):

            first, stream = _peek(stream)

            # Can reverse these objects by slicing while preserving the
            # original type.
            if isinstance(first, (str, list, tuple)):
                yield from (i[::-1] for i in stream)

            else:
                yield from (tuple(reversed(i)) for i in stream)

        # Reverse entire stream
        elif self.directive in ('%revstream', '%reversedstream'):

            # Popping items off of the queue avoids having two copies of the
            # input data in-memory.
            stream = deque(stream)
            while stream:
                yield stream.pop()

        else:  # pragma no cover
            raise RuntimeError(f"invalid directive: {self.directive}")


class OpBatched(OpBase, directives=('%batched', )):

    """Group stream into chunks with no more than N elements.

    Equivalent to ``itertools.batched()``.
    """

    def __init__(self, directive: str, chunksize: int, /, **kwargs):

        """
        :param str directive:
            See parent implementation.
        :param int chunksize:
            Maximum number of items to include in each "batch".
        :param **kwargs kwargs:
            See parent implementation.
        """

        super().__init__(directive, **kwargs)
        self.chunksize = chunksize

    def __call__(self, stream):

        # 'itertools.batched()' was introduced in Python 3.12 and cannot
        # be used
        stream = (i for i in stream)
        while chunk := tuple(it.islice(stream, self.chunksize)):
            yield tuple(chunk)


###############################################################################
# Command Line Interface


_CLI_DESCRIPTION = r"""
It's like sed, but Python!

Map Python expressions across lines of text.  If an expression evaluates as
'False' or 'None' then the current line is thrown away.  If an expression
evaluates as 'True' then the next expression is evaluated.  If a list or
dictionary is encountered it is JSON encoded.  All other objects are cast
to string.

Newline characters are stripped from the end of each line before processing
and are added on write unless disabled with '--no-newline'.

This utility employs 'eval()' internally but uses a limited scope to help
prevent accidental side effects, but there are plenty of ways to get around
this so don't pass anything through pyin that you wouldn't pass through
'eval()'.

Remove lines that do not contain a specific word:

    $ pyin -i file "'word' in line"

Capitalize lines containing a specific word:

    $ pyin -i file "line.upper() if 'word' in line else line"

Only print every other word from lines that contain a specific word:

    $ pyin \
      -i file \
      "'word' in line" \
      "line.split()[::2])" \
      "' '.join(line)"

The '$ pyin' expressions in the command above do:

    1. Select only lines containing 'word'.
    2. Split string on whitespace and select every other word. Note that this
       expression results in a list.
    3. Join list of words into a string.
""".strip()


def _type_variable(value):

    """:mod:`argparse` type caster for ``--variable`` flag.

    Ensures the given variable is valid.
    """

    if not value.isidentifier():
        raise argparse.ArgumentTypeError(
            f'string is not valid as a variable: {value}')

    return value


def _type_gen(value):

    """Ensure ``--gen`` is not combined with piping data to ``stdin``."""

    if not sys.stdin.isatty():
        raise argparse.ArgumentTypeError(
            'cannot combine with piping data to stdin')

    return value


def argparse_parser() -> argparse.ArgumentParser:

    """Construct an :obj:`argparse.ArgumentParser`.

    Provided as an entrypoint to argument parsing that can provide a better
    entrypoint to :func:`main` from Python.
    """

    aparser = argparse.ArgumentParser(
        description=_CLI_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    aparser.add_argument(
        '--version', action='version', version=__version__
    )

    # Input data
    input_group = aparser.add_mutually_exclusive_group()
    input_group.add_argument(
        '--gen', metavar='EXPR', dest='generate_expr', type=_type_gen,
        help="Execute expression and feed results into other expressions."
    )
    input_group.add_argument(
        '-i', '--infile', type=argparse.FileType('r'), default='-',
        help="Read input from this file. Use '-' for stdin (the default)."
    )

    aparser.add_argument(
        '-o', '--outfile', metavar='PATH',
        type=argparse.FileType('w'), default='-',
        help="Write to this file. Use '-' for stdout (the default)."
    )
    aparser.add_argument(
        '--linesep', default=os.linesep, metavar='STR',
        help=f"Write this after every line. Defaults to: {repr(os.linesep)}."
    )
    aparser.add_argument(
        '--variable', default=_DEFAULT_VARIABLE, type=_type_variable,
        help="Place each input item in this variable when evaluating"
             " expressions."
    )
    aparser.add_argument(
        '--stream-variable', default=_DEFAULT_STREAM_VARIABLE,
        type=_type_variable,
        help="Place the stream in this variable when evaluating expressions"
             " against the stream itself."
    )

    aparser.add_argument('expressions', nargs='*')

    return aparser


def _adjust_sys_path(f: Callable) -> Callable:

    """Decorator to ensure :attr:`sys.path` is adjusted properly.

    Being able to reference Python files or modules in the current directory
    is very powerful, but requires an adjustment :attr:`sys.path` that we to
    only manifest in certain contexts.

    Primarily, applying this to :func:`main` allows it to provide an interface
    to the CLI from within Python that also includes the :attr:`sys.path`
    adjustment.

    :param f:
        Function to wrap.
    """

    @functools.wraps(f)
    def inner(*args, **kwargs):

        cleanup = '' not in sys.path
        try:
            if '' not in sys.path:
                sys.path.append('')
            return f(*args, **kwargs)
        finally:
            if cleanup:
                sys.path.pop(sys.path.index(''))

    return inner


@_adjust_sys_path
def main(
        generate_expr: Optional[str],
        infile: TextIO,
        outfile: TextIO,
        expressions: List[str],
        linesep: str,
        variable: str,
        stream_variable: str
) -> int:

    """Command line interface.

    Direct access to the CLI logic. :obj:`argparse.ArgumentParser` can be
    accessed with :func:`parser`.

    :param generate_expr:
        Generate input data from this expression instead of ``infile``.
    :param infile:
        Read text from this file.
    :param outfile:
        Write text to this file.
    :param expressions:
        Evaluate these ``pyin`` expressions on each line of text from
        ``infile``.
    :param linesep:
        Write this after every line.
    :param variable:
        Place each input item in this variable when evaluating expressions.
    :param stream_variable:
        See ``--variable``.

    :returns:
        Exit code.
    """

    # ==== Fetch Input Data Stream ==== #

    # Equivalent to just invoking '$ pyin'. No input files, no piping data
    # to 'stdin', and no '--gen' flag. Technically users can type data into
    # 'stdin' in this mode, but that doesn't seem very useful.
    if generate_expr is None and infile.isatty():
        argparse_parser().print_help()
        return 2

    # Generating data for input.
    elif generate_expr is not None:
        input_stream = eval(
            [generate_expr],
            [object],  # Need something to iterate over
            variable='_'  # Obfuscate the scope a bit
        )

        input_stream = next(input_stream)
        if not isinstance(input_stream, Iterable):
            print(
                "ERROR: '--gen' expression did not produce an iterable"
                " object:", generate_expr, file=sys.stderr)
            return 1

    # Reading from the input file.
    else:
        input_stream = infile

        # Strip newline characters. They are added later.
        input_stream = (i.rstrip(os.linesep) for i in input_stream)

    # ==== Process Data ==== #

    for line in eval(
            expressions, input_stream,
            variable=variable, stream_variable=stream_variable):

        if not isinstance(line, str):
            line = repr(line)

        outfile.write(line)
        outfile.write(linesep)

    return 0


def _cli_entrypoint(rawargs: Optional[list] = None):
    """Shim for CLI entrypoint.

    :func:`main` and :func:`parser` provide an entrypoint to the CLI that can
    also be invoked from Python, but does not work well with ``setuptools``'s
    entrypoint machinery. This shim provides a bridge.

    :param rawargs:
        Like :obj:`sys.argv` (used by default) but without the interpreter
        path. Used in testing.
    """

    args = argparse_parser().parse_args(args=rawargs)

    try:
        exit_code = main(**vars(args))

    # User interrupted with '^C' most likely, but technically this is just
    # a SIGINT. Somehow this shows up in the coverage report generated by
    # '$ pytest --cov'. No idea how that works!!
    except KeyboardInterrupt:
        print()  # Don't get a trailing newline otherwise
        exit_code = 128 + signal.SIGINT

    # A 'RuntimeError()' indicates a problem that should have been caught
    # during testing. We want a full traceback in these cases.
    except RuntimeError:  # pragma no cover
        print(''.join(traceback.format_exc()).rstrip(), file=sys.stderr)
        exit_code = 1

    # Generic error reporting
    except Exception as e:
        print("ERROR:", str(e), file=sys.stderr)
        exit_code = 1

    exit(exit_code)


if __name__ == '__main__':
    _cli_entrypoint()  # pragma no cover
