"""
Commandline interface for pyin
"""


import json
import logging
import os

import click

import pyin
import pyin.core


@click.command(name='pyin')
@click.version_option(pyin.__version__)
@click.option(
    '-i', '--infile', metavar='PATH', type=click.File(mode='r'), default='-',
    help="Input text file. [default: stdin]"
)
@click.option(
    '-o', '--outfile', metavar='PATH', type=click.File(mode='w'), default='-',
    help="Output text file. [default: stdout]"
)
@click.option(
    '--block', is_flag=True,
    help="Operate on all input text as though it was a single line."
)
@click.option(
    '--no-newline', is_flag=True,
    help="Don't ensure each line ends with a newline character."
)
@click.argument(
    'expressions', required=True, nargs=-1,
)
def main(infile, outfile, expressions, no_newline, block):

    """
    It's like sed, but Python!

    \b
    Map Python expressions across lines of text.  If an expression evaluates as
    'False' or 'None' then the current line is thrown away.  If an expression
    evaluates as 'True' then the next expression is evaluated.  If a list or
    dictionary is encountered it is JSON encoded.  All other objects are cast
    to string.

    \b
    Newline characters are stripped from the end of each line before processing
    and are added on write unless disabled with '--no-newline'.

    \b
    This utility employs 'eval()' internally but uses a limited scope to help
    prevent accidental side effects, but there are plenty of ways to get around
    this so don't pass anything through pyin that you wouldn't pass through
    'eval()'.

    \b
    Remove lines that do not contain a specific word:
    \b
        $ cat INFILE | pyin "'word' in line"

    \b
    Capitalize lines containing a specific word:
    \b
        $ cat INFILE | pyin "line.upper() if 'word' in line else line"

    \b
    Only print every other word from lines that contain a specific word:
    \b
        $ cat INFILE | pyin \\
        > "'word' in line" \\      # Get lines with 'word' in them
        > "line.split()[::2])" \\  # Grab every other word
        > "' '.join(line)"         # Convert list from previous expr to str

    \b
    Process all input text as though it was a single line to replace carriage
    returns with the system newline character:
    \b
        $ cat INFILE | pyin --block \\
        > "line.replace('\\r\\n', os.newline)"

    \b
    For a more in-depth explanation about exactly what's going on under the
    hood, see the the docstring in 'pyin.core.pmap()':
    \b
        $ python -c "help('pyin.core.pmap')"
    """

    if block:
        iterator = [infile.read()]
    else:
        iterator = (l.rstrip(os.linesep) for l in infile)

    for line in pyin.core.pmap(expressions, iterator):

        if isinstance(line, (list, tuple, dict)):
            line = json.dumps(line)
        else:
            line = str(line)

        if not no_newline and not line.endswith(os.linesep):
            line += os.linesep

        outfile.write(line)
