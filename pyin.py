"""
Perform Python operations on every line streamed from stdin
"""


import codecs
import os
import sys

import click
from derive import BaseReader as DefaultReader
from derive import BaseWriter as DefaultWriter
from str2type import str2type


__all__ = ['pyin']


__version__ = '0.2.2'
__author__ = 'Kevin Wurster'
__email__ = 'wursterk@gmail.com'
__source__ = 'https://github.com/geowurster/pyin'
__license__ = '''
New BSD License

Copyright (c) 2014, Kevin D. Wurster
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
PY3 = sys.version_info[0] == 3
if PY3:  # pragma no cover
    STR_TYPES = (str)
else:  # pragma no cover
    STR_TYPES = (str, unicode)


def pyin(stream, operation, strip=True, write_true=False, on_true=None):

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
    stream : file
        File-like object that yields one line every iteration.
    operation : string
        Expression to be evaluated by `eval()`.  Lines are accessible via a
        variable named 'line'.
    strip : bool, optional
        Strip trailing whitespace and newline characters.
    write_true : bool, optional
        Only write lines if the operation evaluates as `True`.

    Yields
    ------
    str
        The result of `eval(operation)`.
    """

    for line in stream:
        if strip and hasattr(line, 'rstrip'):
            line = line.rstrip()

        # Only yield lines that evaluate as True
        if not write_true:
            yield eval(operation)
        elif write_true and eval(operation):
            if on_true is not None:
                yield eval(on_true)
            else:
                yield line


def _key_val_to_dict(ctx, param, value):

    """
    Some options like `-ro` take `key=val` pairs that need to be transformed
    into `{'key': 'val}`.  This function can be used as a callback to handle
    all options for a specific flag, for example if the user specifies 3 reader
    options like `-ro key1=val1 -ro key2=val2 -ro key3=val3` then `click` uses
    this function to produce `{'key1': 'val1', 'key2': 'val2', 'key3': 'val3'}`.

    Parameters
    ----------
    ctx : click.Context
        Ignored
    param : click.Option
        Ignored
    value : tuple
        All collected key=val values for an option.

    Returns
    -------
    dict
    """

    output = {}
    for pair in value:
        if '=' not in pair:
            raise ValueError("Incorrect syntax for KEY=VAL argument: `%s'" % pair)
        else:
            key, val = pair.split('=')
            val = str2type(val)
            if isinstance(val, STR_TYPES):
                val = codecs.decode(val, 'unicode_escape')
            output[key] = val

    return output


@click.command()
@click.option(
    '-i', '--i-stream', metavar='STDIN', type=click.File(mode='r'), default='-',
    help="Input stream."
)
@click.option(
    '-o', '--o-stream', metavar='FILE', type=click.File(mode='w'), default='-',
    help="Output stream."
)
@click.option(
    '-im', '--import', 'import_modules', metavar='MODULE', multiple=True,
    help="Import additional modules."
)
@click.option(
    '-nl', '--newline', metavar='CHAR', default=os.linesep,
    help="Output newline character."
)
@click.option(
    '-ns', '--no-strip', is_flag=True, default=True,
    help="Don't call `line.rstrip()` before operation."
)
@click.option(
    '-t', '--write-true', is_flag=True,
    help="Write lines if operation evaluates as True."
)
@click.option(
    '-ot', '--on-true', metavar='OPERATION',
    help="Additional operation if line is True."
)
@click.option(
    '-r', '--reader', metavar='NAME', default='DefaultReader',
    help="Load input stream into the specified reader."
)
@click.option(
    '-ro', '--reader-option', metavar='KEY=VAL', multiple=True, callback=_key_val_to_dict,
    help="Keyword arguments for reader."
)
@click.option(
    '-w', '--writer', metavar='NAME', default='DefaultWriter',
    help="Load output stream into specified writer."
)
@click.option(
    '-wo', '--writer-option', metavar='KEY=VAL', multiple=True, callback=_key_val_to_dict,
    help="Keyword arguments for writer."
)
@click.option(
    '-wm', '--write-method', metavar="NAME", default='write',
    help="Call this method instead of 'writer.write()'."
)
@click.argument(
    'operation', required=True
)
@click.version_option(version=__version__)
def main(i_stream, operation, o_stream, import_modules, newline, no_strip, write_true, reader, reader_option,
         writer, writer_option, write_method, on_true):

    """
    Perform Python operations on every line read from stdin.
    """

    try:

        # Additional imports
        for module in import_modules:
            globals()[module] = __import__(module)

        # Allow user to specify -ot without -t and still enable -t
        if on_true is not None:
            write_true = True

        # Prep reader and writer
        # Readers like csv.DictReader yield lines that aren't strings and since the default writer
        # blindly casts everything to a string, its a lot easier if it just handles the newline character
        # as well so its important to make sure it receives that option.
        if writer == 'DefaultWriter' and 'newline' not in writer_option:
            writer_option['newline'] = newline
        loaded_reader = eval(reader)(i_stream, **reader_option)
        loaded_writer = eval(writer)(o_stream, **writer_option)

        # Stream lines and process
        for output in pyin(loaded_reader, operation, strip=no_strip is True, write_true=write_true, on_true=on_true):
            getattr(loaded_writer, write_method)(output)
        sys.exit(0)

    except Exception as e:
        click.echo("ERROR: Encountered an exception: %s" % repr(e), err=True)
        sys.exit(1)
