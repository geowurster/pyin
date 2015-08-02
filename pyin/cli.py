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
    '--no-newline', is_flag=True,
    help="Don't ensure each line ends with a newline character."
)
@click.argument(
    'expressions', required=True, nargs=-1,
)
def main(infile, outfile, expressions, no_newline):

    """
    Map Python expressions across lines of text.

    This utility is intended to eliminate the overhead associated with doing
    weird one off text transforms and replace-all's that are often done by
    copying output from a console window, pasting it into a text editor or
    IPython via `%paste` where lines are then iterated over, transformed,
    printed to the console, copied, and finally pasted somewhere else.  Instead,
    the original lines can be streamed to `pyin` where the user can perform
    standard Python string expressions or more complicated transforms by setting
    up and tearing down specific readers and writers.

    \b
    Remove all spaces from every line:
    \b
        $ cat ${FILE} | pyin "line.replace(' ', '')"

    \b
    Extract every other word from every line:
    \b
        $ cat ${FILE} | pyin "' '.join(line.split()[::2])
    """

    for line in pyin.core.pmap(expressions, infile):

        if isinstance(line, (list, tuple, dict)):
            line = json.dumps(line)
        else:
            line = str(line)

        if not no_newline and not line.endswith(os.linesep):
            line += os.linesep

        outfile.write(line)
