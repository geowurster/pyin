"""
Perform Python operations on every line streamed from stdin
"""


import sys

import click


__version__ = '0.1.0'
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


def pyin(stream, operation):

    """
    Read lines from an input stream and apply the same operation to every line.

    Parameters
    ----------
    stream : file
        File-like object that yields one line every iteration.
    operation : string
        Expression to be evaluated by `eval()`.  Lines are accessible via a
        variable named 'line'.

    Yields
    ------
    str
        The result of `eval(operation)`.
    """

    for line in stream:
        yield eval(operation)


@click.command()
@click.option(
    '-i', '--i-stream', metavar='STDIN', type=click.File(mode='r'),
    help="Input stream."
)
@click.option(
    '-o', '--o-stream', metavar='FILE', type=click.File(mode='w'),
    help="Output stream."
)
@click.option(
    '-b', '--block', is_flag=True, default=False,
    help="Apply operation to entire input."
)
@click.option(
    '-im', '--import', 'import_modules', metavar='MODULE', multiple=True,
    help="Import module"
)
@click.argument(
    'operation', type=click.STRING, required=True
)
@click.version_option(version=__version__)
def main(i_stream, operation, o_stream, block, import_modules):

    """
    Perform Python operations on every line read from stdin.
    """

    try:

        for module in import_modules:
            globals()[module] = __import__(module)

        if block:
            i_stream = [i_stream.read()]

        # Have to kind of hack click.echo() in order to get it to work in the testing module and here
        # For some reason using o_stream.write() works here but is not captured by the CliRunner()
        # class that is used to test.  The argument 'file' sets the output stream to whatever the user specifies
        # and since the input lines already have a newline character, setting 'nl' to an empty string prevents
        # two newline characters from being written
        for output in pyin(i_stream, operation):
            click.echo(str(output), file=o_stream, nl='')
        sys.exit(0)

    except Exception as e:
        click.echo(e.message, err=True)
        sys.exit(1)
