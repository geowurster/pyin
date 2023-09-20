"""It's like ``sed``, but Python!"""


import argparse
import builtins
import functools
import itertools as it
import sys
import signal
from inspect import isgenerator
import json
import operator
import os
import re
import traceback
from types import CodeType
from typing import Callable, Iterable, Optional, Sequence, TextIO, Tuple, Union


__version__ = '0.5.4'
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
_IMPORTER_REGEX = re.compile(r"([a-zA-Z_.][a-zA-Z0-9_.]*)")



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
def compile(expressions: Union[str, Sequence[str]]) -> Tuple[CodeType]:

    """Compile expressions to Python :module:`code` objects.

    Python's :func:`eval` compiles expressions before executing, but does not
    cache them. Given that we execute each expression as much as once per
    line, we can achieve a noticeable speedup by pre-compiling the expressions.

    :param expressions:
        Expressions to compile.
    """

    compiled = []

    for expr in expressions:
        try:
            code = builtins.compile(expr, '<expression>', 'eval')
        except SyntaxError as e:
            msg = (f"could not compile expression:"
                   f" {expr}{os.linesep}{os.linesep}{traceback.format_exc(0)}")
            raise SyntaxError(msg) from e

        compiled.append(code)

    return tuple(compiled)


@_normalize_expressions
def importer(
        expressions: Union[str, Sequence[str]],
        scope: Optional[dict] = None
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
        Import modules into this scope. By default, a new scope is created
        with every call, but data can be imported into an existing scope by
        passing a dictionary.
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
def eval(expressions, iterable, variable='line'):

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

    global_scope = {
        'it': it,
        'op': operator,
        'reduce': functools.reduce}

    importer(expressions, scope=global_scope)
    compiled_expressions = compile(expressions)

    for idx, obj in enumerate(iterable):

        for expr in compiled_expressions:

            result = builtins.eval(
                expr, global_scope, {'idx': idx, variable: obj})

            # Got a generator.  Expand and continue.
            if isgenerator(result):
                obj = list(result)

            # Result is some object.  Pass it back in under 'variable'.
            elif not isinstance(result, bool):
                obj = result

            # Result is True/False.  Only continue if True.
            # Have to explicitly let string_types through for ''
            # which would otherwise be ignored.
            elif isinstance(result, str) or result:
                continue

            # Got something else?  Halt processing for this obj.
            else:
                obj = None
                break

        # Have to explicitly let string_types through for ''
        # which would otherwise be ignored.
        if isinstance(obj, str) or isinstance(obj, (int, float)) or obj:
            yield obj


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
        '--no-newline', action='store_true',
        help="Don't ensure each line ends with a newline character."
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


def main(
        generate_expr: Optional[str],
        infile: TextIO,
        outfile: TextIO,
        expressions: list[str],
        no_newline: bool,
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
    :param no_newline:
        Do not append a line separator to the end of each line.
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

    # Piping data to stdin combined with '--gen' is not allowed.
    if generate_expr is not None and not infile.isatty():
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

        if isinstance(line, str):
            pass
        elif isinstance(line, (list, tuple, dict)):
            line = json.dumps(line)
        else:
            line = repr(line)

        if not no_newline and not line.endswith(os.linesep):
            line += os.linesep

        outfile.write(line)

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
    # a SIGINT.
    except KeyboardInterrupt:
        print()  # Don't get a trailing newline otherwise
        exit_code = 128 + signal.SIGINT

    exit(exit_code)


if __name__ == '__main__':
    _cli_entrypoint()
