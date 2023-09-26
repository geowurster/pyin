"""It's like ``sed``, but Python!"""


import abc
import argparse
import builtins
import functools
import importlib
import inspect
import itertools as it
import sys
import signal
import operator as op
import os
import re
from types import CodeType
from typing import (
    Any, Callable, Iterable, List, Optional, Sequence, TextIO, Tuple, Union)


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


_DEFAULT_VARIABLE = 'line'
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
        scope: Union[None, dict] = None
) -> Tuple[CodeType]:

    """Compile expressions to Python :module:`code` objects.

    Python's :func:`eval` compiles expressions before executing, but does not
    cache them. Given that we execute each expression as much as once per
    line, we can achieve a noticeable speedup by pre-compiling the expressions.

    :param expressions:
        Expressions to compile.
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
            directive = Eval.directives[0]

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
        args.extend(p.annotation(tokens.pop(0)) for p in pos_only[1:])
        kwargs = {
            'variable': variable,
            'scope': scope
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
        # imported, like a class method.
        except ImportError:
            res = importlib.util.find_spec(module)
            if res is not None:
                raise ImportError(
                    f"attempting to import something that cannot be imported"
                    f" from a module that does exist: {match}"
                )  # pragma no cover

    return scope


@_normalize_expressions
def eval(expressions, stream, variable: str = _DEFAULT_VARIABLE):

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
    """

    scope = {
        'it': it,
        'op': op,
        'reduce': functools.reduce
    }
    if all(isinstance(e, str) for e in expressions):
        importer(expressions, scope=scope)

    compiled_expressions = compile(expressions, variable=variable, scope=scope)

    for callable in compiled_expressions:
        stream = callable(stream)

    yield from stream


###############################################################################
# Operations


def _first(sequence: Sequence) -> Tuple[Any, Sequence]:

    """Peek at a stream of data.

    Note that the output sequence is not guaranteed to be of the same type
    as the input sequence. The output sequence is guaranteed to be iterable.

    :param sequence:
        Peek at first value in this sequence.

    :return:
        A ``tuple`` with two elements. The first is the next value in
        ``sequence``, and the second is the reconstructed sequence.
    """

    sequence = (i for i in sequence)
    first = next(sequence)
    return first, it.chain([first], sequence)


class BaseOperation(abc.ABC):

    """Base class for defining an operation.

    Subclassers can use positional-only arguments and type annotations in
    :meth:`__init__` to define arguments associated with the directive and
    their type.
    """

    def __init__(self, directive: str, /, variable: str, scope: dict):

        """
        :param directive:
            The directive actually usd in the expressions. Some operation
            classes can support multiple directives.
        :param variable:
            Operations executing expressions with Python's :obj:`eval` should
            place data in this variable in the scope.
        :param scope:
            Operations executing expressions with Python's :obj:`eval` should
            execute in this scope.
        """

        self.directive = directive
        self.variable = variable
        self.scope = scope

        if self.directive not in self.directives:
            raise ValueError(
                f"instantiated '{repr(self)}' with directive"
                f" '{self.directive}' but supports:"
                f" {' '.join(self.directives)}"
            )

    def __init_subclass__(cls, /, directives: Sequence, **kwargs):

        """Register mapping of directives to classes.

        Also populates ``Operations.directives`` class variable.

        :param directives:
            Sequence of directives like ``('%upper', '%lower')`` supported by
            this class.
        :param **kwargs:
            Arguments for class.
        """

        super().__init_subclass__(**kwargs)

        global _DIRECTIVE_REGISTRY

        for d in directives:
            if d in _DIRECTIVE_REGISTRY:
                raise RuntimeError(
                    f"directive '{d}' conflict:"
                    f" {cls} {_DIRECTIVE_REGISTRY[d]}")

            cls.directives = directives
            _DIRECTIVE_REGISTRY[d] = cls

    def __repr__(self) -> str:

        """Approximate representation of :obj:`BaseOperation` instance."""

        return f"<{self.__class__.__name__}({self.directive})>"

    @abc.abstractmethod
    def __call__(self, stream: Sequence) -> Sequence:

        """Process a stream of data.

        :param stream:
            Input data stream.

        :return:
            Altered data.
        """

        raise NotImplementedError  # pragma no cover


class Eval(BaseOperation, directives=('%eval', )):

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


class Filter(Eval, directives=('%filter', '%filterfalse')):

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


class Accumulate(
    BaseOperation, directives=('%acc', '%accumulate', '%collect')):

    """Accumulate the entire stream into a single object."""

    def __call__(self, stream):
        yield list(stream)


class Flatten(BaseOperation, directives=('%explode', '%flatten', '%chain')):

    """Flatten the stream by one level – like :obj:`itertools.chain`."""

    def __call__(self, stream):
        return it.chain.from_iterable(stream)


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


def cli_parser() -> argparse.ArgumentParser:

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
        '--gen', metavar='EXPR', dest='generate_expr',
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
        '--block', action='store_true',
        help="Place all input text into the `line` variable."
    )
    aparser.add_argument(
        '--linesep', default=os.linesep, metavar='STR',
        help=f"Write this after every line. Defaults to: {repr(os.linesep)}."
    )
    aparser.add_argument(
        '--skip', dest='skip_lines', type=int, default=0,
        help="Skip N lines in the input text stream before processing. When "
             "operating in block processing mode the lines are skipped before"
             " the text is converted to a block. When operating on multiple"
             " input only lines in the first file are skipped."
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
        block: bool,
        skip_lines: int
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
    :param block:
        Treat all input lines as a single line of text. Equivalent to reading
        all input data into a single :obj:`str` and running that through
        ``expressions``.
    :param skip_lines:
        Skip the first N lines of the input stream.

    :returns:
        Exit code.
    """

    # ==== Fetch Input Data Stream ==== #

    # Equivalent to just invoking '$ pyin'. No input files, no piping data
    # to 'stdin', and no '--gen' flag. Technically users can type data into
    # 'stdin' in this mode, but that doesn't seem very useful.
    if generate_expr is None and infile.isatty():
        cli_parser().print_help()
        return 2

    # Piping data to stdin combined with '--gen' is not allowed.
    elif generate_expr is not None and not infile.isatty():
        raise argparse.ArgumentError(
            None, "cannot combine '--gen' with piping data to stdin")

    # Generating data for input. Must also handle '--block' because the
    # behavior differs for something like a sequence of floats vs. just
    # a 'f.read()' for the input file.
    elif generate_expr is not None:
        input_stream = eval(
            [generate_expr],
            [object],  # Need something to iterate over
            variable='_'  # Obfuscate the scope a bit
        )

        input_stream = next(input_stream)
        if not isinstance(input_stream, Iterable):
            print(
                f"ERROR: '--gen' expression did not produce an iterable"
                f" object:", generate_expr, file=sys.stderr)
            return 1

        # --skip
        input_stream = (i for i in input_stream)
        for _ in range(skip_lines):
            try:
                next(input_stream)
            except StopIteration:
                break

        if block:
            input_stream = [input_stream]

    # Reading from the input file. Need to handle '--block' and '--skip' due
    # to inherent differences for what these mean for '--gen'.
    else:

        # --skip
        for _ in range(skip_lines):
            try:
                next(infile)
            except StopIteration:
                break

        if block:
            input_stream = [infile.read()]
        else:
            input_stream = infile

        # Strip newline characters. They are added later.
        input_stream = (i.rstrip(os.linesep) for i in input_stream)

    # ==== Process Data ==== #

    for line in eval(expressions, input_stream):

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

    args = cli_parser().parse_args(args=rawargs)

    try:
        exit_code = main(**vars(args))

    # Some conflicting arguments/states can only be detected at runtime
    except argparse.ArgumentError as e:
        print("ERROR:", e.message, file=sys.stderr)
        exit_code = 1

    # User interrupted with '^C' most likely, but technically this is just
    # a SIGINT. Somehow this shows up in the coverage report generated by
    # '$ pytest --cov'. No idea how that works!!
    except KeyboardInterrupt:
        print()  # Don't get a trailing newline otherwise
        exit_code = 128 + signal.SIGINT

    # Generic error reporting
    except Exception as e:
        print("ERROR:", str(e), file=sys.stderr)
        exit_code = 1

    exit(exit_code)


if __name__ == '__main__':
    _cli_entrypoint()  # pragma no cover
