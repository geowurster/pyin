"""
Perform Python expressions on every line streamed from stdin
"""


import sys as _sys

import click as _click
import str2type as _str2type


__all__ = ['pyin']


__version__ = '0.3.5'
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


# Python 2/3 compatibility
_PY3 = _sys.version_info[0] == 3
if _PY3:  # pragma no cover
    _STR_TYPES = (str)
else:  # pragma no cover
    _STR_TYPES = (str, unicode)


def pyin(expression, reader, write_true=False, on_true=None):

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

    Yields
    ------
    <object>
        The result of `eval(expression)`.
    """

    # Don't let the user have access to variables they don't need access to.
    _expression = expression
    del expression
    _write_true = write_true
    del write_true
    _on_true = on_true
    del on_true

    for _idx, line in enumerate(reader):

        # Only yield lines that evaluate as True
        if not _write_true:
            yield eval(_expression)

        # expression evaluated as True
        elif _write_true and eval(_expression):

            # Apply an additional expression if specified
            if _on_true is not None:
                yield eval(_on_true)

            # Just yield the line
            else:
                yield line


class _DefaultReader(object):

    def __init__(self, f):
        self.f = f

    def __iter__(self):
        return self

    def next(self):
        return next(self.f)

    __next__ = next


class _DefaultWriter(object):

    def __init__(self, f):
        self.f = f

    def write(self, line):
        self.f.write(line)


@_click.command()
@_click.option(
    '-i', '--i-stream', metavar='STDIN', type=_click.File(mode='r'), default='-',
    help="Input stream."
)
@_click.option(
    '-o', '--o-stream', metavar='FILE', type=_click.File(mode='w'), default='-',
    help="Output stream."
)
@_click.option(
    '-im', '--import', 'import_modules', metavar='MODULE', multiple=True,
    help="Import additional modules."
)
@_click.option(
    '-t', '--write-true', is_flag=True,
    help="Write lines if expression evaluates as True."
)
@_click.option(
    '-ot', '--on-true', metavar='expression',
    help="Additional expression if line is True."
)
@_click.option(
    '-r', '--reader', metavar='NAME', default='_DefaultReader',
    help="Load input stream into the specified reader."
)
@_click.option(
    '-ro', '--reader-option', metavar='KEY=VAL', multiple=True, callback=_str2type.click_callback_key_val_dict,
    help="Keyword arguments for reader."
)
@_click.option(
    '-w', '--writer', metavar='NAME', default='_DefaultWriter',
    help="Load output stream into specified writer."
)
@_click.option(
    '-wo', '--writer-option', metavar='KEY=VAL', multiple=True, callback=_str2type.click_callback_key_val_dict,
    help="Keyword arguments for writer."
)
@_click.option(
    '-wm', '--write-method', metavar="NAME", default='write',
    help="Call this method instead of `writer.write()`."
)
@_click.option(
    '-b', '--block', is_flag=True,
    help="Treat all input text as a single line."
)
@_click.option(
    '-v', '--variable', metavar='VAR=VAL', multiple=True, callback=_str2type.click_callback_key_val_dict,
    help="Assign variables for access in expression."
)
@_click.option(
    '-s', '--statement', metavar='CODE', multiple=True,
    help="Execute a statement after imports."
)
@_click.option(
    '-l', '--lines', metavar='N', type=_click.INT,
    help="Only process N lines."
)
@_click.argument(
    'expression', required=True
)
@_click.version_option(version=__version__)
def main(i_stream, expression, o_stream, import_modules, write_true, reader, reader_option,
         writer, writer_option, write_method, on_true, block, variable, statement, lines):

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

    try:

        # Validate arguments
        if lines is not None and lines < 0:
            _click.echo("ERROR: Invalid number of lines: `%s' - must be a positive int or None", err=True)
            _sys.exit(1)

        # Additional imports
        for module in import_modules:
            globals()[module] = __import__(module)

        # Execute additional statements
        for s in statement:
            exec(s)

        # Assign additional variables
        for var, val in variable.items():
            globals()[var] = val

        # Allow user to specify -ot without -t and still enable -t
        if on_true is not None:
            write_true = True

        # Prepare block mode, where all lines are processed together in a single block of text
        if block:
            i_stream = iter([i_stream.read()])

        # Prep reader and writer
        loaded_reader = eval(reader)(i_stream, **reader_option)
        loaded_writer = eval(writer)(o_stream, **writer_option)

        # Stream lines and process
        _write_method = getattr(loaded_writer, write_method)
        for idx, output in enumerate(pyin(expression, loaded_reader, write_true=write_true, on_true=on_true)):

            # Only process N lines
            if lines is not None and lines is idx:
                break

            _write_method(output)

        _sys.exit(0)

    except Exception as e:
        _click.echo("ERROR: Encountered an exception: %s" % repr(e), err=True)
        _sys.exit(1)
