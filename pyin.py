"""
Perform Python operations on every line streamed from stdin
"""


import os as _os
import sys as _sys

import click as _click
from derive import BaseReader as _DefaultReader
from derive import BaseWriter as _DefaultWriter
import str2type as _str2type


__all__ = ['pyin']


__version__ = '0.3.3'
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


def pyin(reader, operation, strip=True, write_true=False, on_true=None):

    """
    Read lines from an input stream and apply the same operation to every line.

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
    operation : string
        Expression to be evaluated by `eval()`.  Lines are accessible via a
        variable named 'line'.
    strip : bool, optional
        Strip trailing whitespace and linesep characters.
    write_true : bool, optional
        Only write lines if the operation evaluates as `True`.

    Yields
    ------
    str
        The result of `eval(operation)`.
    """

    # Don't let the user have access to variables they don't need access to.
    _operation = operation
    del operation
    _strip = strip
    del strip
    _write_true = write_true
    del write_true
    _on_true = on_true
    del on_true

    for line in reader:
        if _strip and hasattr(line, 'rstrip'):
            line = line.rstrip()

        # Only yield lines that evaluate as True
        if not _write_true:
            yield eval(_operation)
        elif _write_true and eval(_operation):
            if _on_true is not None:
                yield eval(_on_true)
            else:
                yield line


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
    '-ls', '--linesep', metavar='CHAR', default=_os.linesep,
    help="Output linesep character."
)
@_click.option(
    '-ns', '--no-strip', is_flag=True, default=True,
    help="Don't call `line.rstrip()` before operation."
)
@_click.option(
    '-t', '--write-true', is_flag=True,
    help="Write lines if operation evaluates as True."
)
@_click.option(
    '-ot', '--on-true', metavar='OPERATION',
    help="Additional operation if line is True."
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
    help="Assign variables for access in operation."
)
@_click.option(
    '-s', '--statement', metavar='CODE', multiple=True,
    help="Execute a statement after imports."
)
@_click.argument(
    'operation', required=True
)
@_click.version_option(version=__version__)
def main(i_stream, operation, o_stream, import_modules, linesep, no_strip, write_true, reader, reader_option,
         writer, writer_option, write_method, on_true, block, variable, statement):

    """
    Perform Python operations on every line read from stdin.
    """

    try:

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

        # Prepare block mode
        if block:
            i_stream = iter([i_stream.read()])

        # Prep reader and writer
        # Readers like csv.DictReader yield lines that aren't strings and since the default writer
        # blindly casts everything to a string, its a lot easier if it just handles the linesep character
        # as well so its important to make sure it receives that option.
        if writer == '_DefaultWriter' and 'linesep' not in writer_option:
            writer_option['linesep'] = linesep
        loaded_reader = eval(reader)(i_stream, **reader_option)
        loaded_writer = eval(writer)(o_stream, **writer_option)

        # Stream lines and process
        for output in pyin(loaded_reader, operation, strip=no_strip is True, write_true=write_true, on_true=on_true):
            getattr(loaded_writer, write_method)(output)
        _sys.exit(0)

    except Exception as e:
        _click.echo("ERROR: Encountered an exception: %s" % repr(e), err=True)
        _sys.exit(1)
