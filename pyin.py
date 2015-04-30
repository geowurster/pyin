"""
Perform Python expressions on every line streamed from stdin
"""


import os
import sys
try:  # pragma no cover
    from io import StringIO
except ImportError:  # pragma no cover
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
import time

import click
import str2type.ext


__all__ = ['pyin']


__version__ = '0.4.4'
__author__ = 'Kevin Wurster'
__email__ = 'wursterk@gmail.com'
__source__ = 'https://github.com/geowurster/pyin'
__license__ = '''
New BSD License

Copyright (c) 2015, Kevin D. Wurster
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* The names of its contributors may not be used to endorse or promote products
  derived from this software without specific prior written permission.

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

_WAIT_TIME = 30
_NO_WARN_ENV_KEY = "PYIN_NO_WARN"
_NO_WARN_ENV_VAL = "I_read_the_rules_and_accept_the_consequences"


RULES = """
This utility uses `exec()` and `eval()`, which can be dangerous when misused.
Observing the following overly cautious rules will help.

    1. Don't call `eval()` in an expression - this will hopefully be locked out
       in a future release.
    2. Use at your own risk.
    3. Don't trust your input text or code that you're using for reading and
       writing?  Don't use pyin.
    4. Don't use this in a production environment.  The intended use is for
       filtering and transforming a relatively small number of input lines that
       would normally take a few lines of boilerplate Python code you find
       yourself writing over and over.
    5. Before developing a more complicated expression use `"line"` and only
       process a subsample.  This expression passes text through without any
       alterations to make sure the input is as expected.
    6. Like most of Python this utility leaves the locks off the door in favor
       of flexibility and more readable code.  The source code is short, well
       commented, and is worth reading to better understand what is happening
       behind the scenes.
    7. Just because pyin can do it doesn't mean pyin should do it.
    8. This may not be the utility for you.  Use only if confident.

See GitHub for source code, readme, and examples: {github_url}

In order to suppress this message and eliminate the {wait_time} wait, set an environment
variable called `PYIN_NO_WARN` equal to `I_read_the_rules_and_accept_the_consequences`.
""".format(wait_time=_WAIT_TIME, github_url=__source__)


# Python 2/3 compatibility
PY3 = sys.version_info[0] == 3
if PY3:  # pragma no cover
    STR_TYPES = (str)
else:  # pragma no cover
    STR_TYPES = (str, unicode)


def pyin(expression, reader, scope=None, write_true=False, on_true=None):

    """
    Read lines from an input stream and apply the same expression to every line.

    Examples
    --------

    Change all lines to uppercase:

    >>> import os
    >>> import sys
    >>> from pyin import pyin
    >>> with open('sample-data/csv-with-header.csv') as f:
    ...    for line in pyin(f, "line.upper()"):
    ...         sys.stdout.write(line + os.linesep)

    Extract the second column from a CSV:

    >>> import os
    >>> from pyin import pyin
    >>> with open('sample-data/csv-with-header.csv') as f:
    ...     for line in pyin(f, "line.split(',')[1]"):
    ...         sys.stdout.write(line + os.linesep)

    Parameters
    ----------
    reader : file
        File-like object that yields one line every iteration.
    expression : string
        Expression to be evaluated by `eval()`.  Lines are accessible via a
        variable named 'line'.
    write_true : bool, optional
        Only write lines if the expression evaluates as `True`.

    Raises
    ------
    AttributeError
        If 'line' appears in scope.

    Yields
    ------
    <object>
        The result of `eval(expression)`.
    """

    if scope is None:
        scope = {}

    if 'line' in scope:
        raise NameError("Variable 'line' cannot be in scope - will be overwritten by local variable.")

    for _idx, line in enumerate(reader):

        scope['line'] = line

        # Only yield lines that evaluate as True
        if not write_true:
            yield eval(expression, scope)

        # expression evaluated as True
        elif write_true and eval(expression, scope):

            # Apply an additional expression if specified
            if on_true is not None:
                yield eval(on_true, scope)

            # Just yield the line
            else:
                yield line


def _print_rules_callback(ctx, param, value):

    """
    Click callback for `--rules` - immediately prints the rules and exits.
    """

    if not value or ctx.resilient_parsing:
        return None
    click.echo(RULES)
    ctx.exit(0)


def _parse_scope(scope, string_lookup):

    """
    Extract objects from an object like `globals()` given a string containing
    a dotted lookup.

    Example:

        >>> scope = {
        ...     'csv': __import__('csv')
        ... }
        >>> string_lookup = 'csv.DictReader'
        >>> obj = _parse_scope(scope, string_lookup)
        <class csv.DictReader at 0x10aedd120>

    Parameters
    ----------
    scope : dict
        A dictionary like `globals()`
    string_lookup : str
        Dotted string lookup referencing an object in `scope`.
    """

    obj = scope[string_lookup.split('.')[0]]
    for item in string_lookup.split('.')[1:]:
        obj = getattr(obj, item)
    return obj


class _DefaultReader(object):

    def __init__(self, f):

        """
        Default reader - acts like `file` but accepts an already open file-like
        object or any iterable object.

        Attributes
        ----------
        f : file or iterable
            Handle to input iterable

        Parameters
        ----------
        f : file or iterable
            Open file-like object for reading.
        """

        self._f = f

    @property
    def f(self):
        return self._f

    def __iter__(self):
        return self

    def next(self):
        if not PY3:  # pragma no cover
            return self.f.next()
        else:  # pragma no cover
            return self.f.__next__()

    __next__ = next


class _DefaultWriter(object):

    def __init__(self, f):

        """
        Default writer - acts like file but accepts an already open file-like
        object.  Blindly casts all written lines to a string.  Does not add
        a newline character.

        Attributes
        ----------
        f : file
            Handle to open file-like object for writing.
        """

        self._f = f

    @property
    def f(self):
        return self._f

    def write(self, line):

        """
        Blindly casts input lines to a string.  Does not add or modify newline
        characters.
        """

        self.f.write(str(line))


@click.command()
@click.option(
    '-i', '--i-stream', metavar='PATH', type=click.File(mode='r'), default='-',
    help="Input file - if not supplied defaults to stdin."
)
@click.option(
    '-o', '--o-stream', metavar='PATH', type=click.File(mode='w'), default='-',
    help="Output file - if not supplied defaults to stdout."
)
@click.option(
    '-im', '--import', 'import_modules', metavar='MODULE', multiple=True,
    help="Import additional modules.  Use `other=mod.something` for `from mod"
         " import something as other` syntax."
)
@click.option(
    '-t', '--write-true', is_flag=True,
    help="Write lines if expression evaluates as True."
)
@click.option(
    '-ot', '--on-true', metavar='EXPRESSION',
    help="Additional expression to apply to lines that evaluate as `True`."
         "  Automatically enables `--true` flag."
)
@click.option(
    '-r', '--reader', 'reader_name', metavar='MODULE.OBJECT',
    help="Load input stream into the specified reader."
)
@click.option(
    '-ro', '--reader-option', metavar='KEY=VAL', multiple=True, callback=str2type.ext.click_cb_key_val,
    help="Keyword arguments for reader."
)
@click.option(
    '-w', '--writer', 'writer_name', metavar='MODULE.OBJECT',
    help="Load output stream into specified writer."
)
@click.option(
    '-wo', '--writer-option', metavar='KEY=VAL', multiple=True, callback=str2type.ext.click_cb_key_val,
    help="Keyword arguments for writer."
)
@click.option(
    '-wm', '--write-method', metavar="NAME", default='write',
    help="Call this method instead of `writer.write()`."
)
@click.option(
    '-b', '--block', is_flag=True,
    help="Treat all input text as a single line."
)
@click.option(
    '-v', '--variable', metavar='VAR=VAL', multiple=True, callback=str2type.ext.click_cb_key_val,
    help="Assign additional variables for access in expression."
)
@click.option(
    '-s', '--statement', metavar='CODE', multiple=True,
    help="Execute a statement immediately before processing input data."
)
@click.option(
    '-l', '--lines', metavar='N', type=click.INT,
    help="Only process N lines."
)
@click.option(
    '-sl', '--skip-lines', metavar='N', type=click.INT,
    help="Skip the first N lines."
)
@click.option(
    '--rules', is_flag=True, callback=_print_rules_callback, expose_value=False, is_eager=True,
    help='Print the "Rules of pyin" and exit.'
)
@click.argument(
    'expression', required=True
)
@click.version_option(version=__version__)
def main(i_stream, expression, o_stream, import_modules, write_true, reader_name, reader_option,
         writer_name, writer_option, write_method, on_true, block, variable, statement, lines, skip_lines):

    """
    Perform simple Python expressions on every line read from stdin.

    Fair warning: this project utilizes `eval()` and `expr()`.  For more
    information see: https://github.com/geowurster/pyin/blob/master/README.md

    This utility is intended to eliminate the overhead associated with doing
    weird one off text transforms and replace-all's that are often done by
    copying output from a console window, pasting it into a text editor or
    IPython via `%paste` where lines are then iterated over, transformed,
    printed to the console, copied, and finally pasted somewhere else.  Instead,
    the original lines can be streamed to `pyin` where the user can perform
    standard Python string expressions or more complicated transforms by setting
    up and tearing down specific readers and writers.

    Remove all spaces from every line:
    $ cat ${FILE} | pyin "line.replace(' ', '')"

    Extract every other word from every line:
    $ cat ${FILE} | pyin "' '.join(line.split()[::2])

    For more examples, see the cookbook.
    https://github.com/geowurster/pyin/blob/master/Cookbook.md
    """

    # Print the rules and wait before executing a command if the user hasn't set the proper environment variables
    if _NO_WARN_ENV_KEY not in os.environ or os.environ[_NO_WARN_ENV_KEY] != _NO_WARN_ENV_VAL:
        click.echo(RULES, err=True)
        time.sleep(_WAIT_TIME)

    # This is the scope that is used for all eval and exec calls
    # All imported modules and user assigned variables are stored in here
    scope = {}

    try:

        # Validate arguments
        if lines is not None and lines < 0:
            click.echo("ERROR: Invalid number of lines: `%s' - must be a positive int or None.", err=True)
            sys.exit(1)
        if skip_lines is not None and skip_lines < 0:
            click.echo("ERROR: Invalid number of skip lines: `%s' - must be a positive int or None.", err=True)
            sys.exit(1)

        # Add additional imports to the operating scope
        for module in import_modules:
            if '=' in module:
                _new_name, _module_string = module.split('=')
                scope[_new_name] = __import__(_module_string, fromlist=[_module_string.split('.')[0]])
            else:
                scope[module] = __import__(module)

        # Assign additional variables
        for var, val in variable.items():
            scope[var] = val

        # Allow user to specify -ot without -t and still enable -t
        if on_true is not None:
            write_true = True

        # Prepare block mode, where all lines are processed together in a single block of text
        if block:
            i_stream = iter([i_stream.read()])

        # Prep reader and writer - keep _DefaultReader/Writer out of the scope by calling directly
        if reader_name is None:
            scope['reader'] = _DefaultReader(i_stream)
        else:
            scope['reader'] = _parse_scope(scope, reader_name)(i_stream, **reader_option)
        if writer_name is None:
            scope['writer'] = _DefaultWriter(o_stream)
        else:
            scope['writer'] = _parse_scope(scope, writer_name)(o_stream, **writer_option)

        # Execute additional statements
        # expr adds __builtins__ to the scope so remove them afterwards
        for s in statement:
            exec(s, scope)
        if '__builtins__' in scope:
            del scope['__builtins__']

        # Stream lines and process
        write_method_obj = getattr(scope['writer'], write_method)
        processed_lines = 0
        for idx, output in enumerate(
                pyin(expression, scope['reader'], scope=scope, write_true=write_true, on_true=on_true)):

            # Handle skipping input lines and only processing a subsample
            if skip_lines is not None and idx + 1 <= skip_lines:
                continue
            elif lines is not None and lines is processed_lines:
                break

            write_method_obj(output)
            processed_lines += 1

        sys.exit(0)

    except Exception as e:
        click.echo("ERROR: Encountered an exception: %s" % repr(e), err=True)
        sys.exit(1)
