"""
Perform Python operations on every line streamed from stdin
"""


import os
import sys

import click
from str2type import str2type


__version__ = '0.2.1'
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


def pyin(stream, operation, strip=True, write_true=False):

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
        line = line.rstrip()

        # Only yield lines that evaluate as True
        if not write_true:
            yield eval(operation)
        elif write_true and eval(operation):
            yield line


def _parse_key_vals(key_vals):

    """
    Parse `KEY=VAL` pairs collected from the commandline
    Turns: `['k1=v1', 'k2=v2']`
    Into: `{'k1': 'v1', 'k2': 'v2'}`

    Parameters
    ----------
    key_vals : tuple or list

    Raises
    ------
    ValueError
        Key=val pair does not contain an '='.

    Returns
    -------
    dict
        Parsed {'key1': 'val1', 'key2': 'val2}
    """

    return {pair.split('=')[0]: str2type(pair.split('=')[1]) for pair in key_vals}


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
    '-b', '--block', is_flag=True, default=False,
    help="Apply operation to entire input."
)
@click.option(
    '-m', '--import', 'import_modules', metavar='MODULE', multiple=True,
    help="Import additional modules."
)
@click.option(
    '-l', '--linesep', metavar='CHAR', default=os.linesep,
    help="Output linesep character."
)
@click.option(
    '-n', '--no-strip', is_flag=True, default=True,
    help="Don't strip trailing linesep and whitespace on read."
)
@click.option(
    '-t', '--write-true', is_flag=True,
    help="Write lines if the operation evaluates as True."
)
@click.option(
    '-r', '--reader', metavar='NAME',
    help="Load input stream into the specified reader."
)
@click.option(
    '-ro', '--reader-option', metavar='KEY=VAL', multiple=True,
    help="Keyword arguments for reader."
)
@click.option(
    '-w', '--writer', metavar='NAME',
    help="Load output stream into specified writer."
)
@click.option(
    '-wo', '--writer-option', metavar='KEY=VAL', multiple=True,
    help="Keyword arguments for writer."
)
@click.option(
    '-wm', '--write-method', metavar="NAME", default='write',
    help="Call this method instead of 'writer.write()'."
)
@click.argument(
    'operation', type=click.STRING, required=True
)
@click.version_option(version=__version__)
def main(i_stream, operation, o_stream, block, import_modules, linesep, no_strip, write_true,
         reader, reader_option, writer, writer_option, write_method):

    """
    Perform Python operations on every line read from stdin.
    """

    # Parse and format key=val reader/writer options immediately
    if reader_option:
        reader_option = _parse_key_vals(reader_option)
    else:
        reader_option = {}
    if writer_option:
        writer_option = _parse_key_vals(writer_option)
    else:
        writer_option = {}

    try:

        # Additional imports
        for module in import_modules:
            globals()[module] = __import__(module)

        # Prepare input for block processing mode by reading everything into a single string inside of a list
        # The block will be processed on the first and only iteration.
        if block:
            i_stream = [i_stream.read()]

        # Create reader if specified otherwise just use the input stream
        if reader is not None:
            _reader_class = eval(reader)
            loaded_reader = _reader_class(i_stream, **reader_option)

        else:
            loaded_reader = i_stream

        # Create reader if specified otherwise just use the input stream
        if writer is not None:
            _writer_class = eval(writer)
            loaded_writer = _writer_class(o_stream, **writer_option)
            loaded_writer.__class__.__dict__['write'] = loaded_writer.__class__.__dict__[write_method]
        else:
            loaded_writer = o_stream

        # Stream lines and process
        for output in pyin(loaded_reader, operation, strip=no_strip is True, write_true=write_true):
            if linesep:
                output += linesep
            loaded_writer.write(output)
        sys.exit(0)

    except Exception as e:
        click.echo("ERROR: Encountered an exception: %s" % repr(e), err=True)
        sys.exit(1)
