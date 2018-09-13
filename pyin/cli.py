"""
Commandline interface for pyin
"""


import functools
import itertools as it
import operator as op
import os
import sys

import click

import pyin
import pyin.evaluate
from pyin import _compat


@click.command(name='pyin')
@click.version_option(pyin.__version__)
@click.option(
    '-i', '--infile', 'infiles', metavar='PATH', type=click.File(mode='r'),
    default='-', multiple=True, show_default=True,
    help="Input text file.  Use '-' for stdin.  Can be used multiple times to "
         "specify multiple input files, which is like: $ cat * | pyin")
@click.option(
    '-o', '--outfile', metavar='PATH', type=click.File(mode='w'),
    default='-', show_default=True,
    help="Output text file.  Use '-' for stdout.")
@click.option(
    '--block', '-b', is_flag=True,
    help="Place all input text into the `line` variable.")
@click.option(
    '--skip', 'skip_lines', type=click.IntRange(0), metavar='INTEGER',
    default=0,
    help='Skip N lines in the input text stream before processing.  When '
         'operating in block processing mode the lines are skipped before the '
         'text is converted to a block.  When operating on multiple input '
         'only lines in the first file are skipped.')
@click.option(
    '--kis', '--keep-input-linesep', 'keep_input_linesep',
    is_flag=True, default=False,
    help="Do not remove line separator from input lines.")
@click.option(
    '--join',
    default=os.linesep, show_default=repr(os.linesep),
    help="Insert this string between output lines in a manner similar to"
         " 'str.join()'.  By default each item in the output is emitted on"
         " a separate line.  Use an empty string to emit all output on a"
         " single line.")
@click.option(
    '--gen', metavar='EXPR',
    help="Generate input data using an expression.")
@click.argument(
    'expressions', required=True, nargs=-1)
@click.pass_context
def main(
        ctx,
        block,
        expressions,
        gen,
        infiles,
        keep_input_linesep,
        join,
        outfile,
        skip_lines):

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
    hood, see the the docstring in 'pyin.evaluate()':
    \b
        $ python -c "help('pyin.evaluate')"
    """

    if gen and block:
        raise click.BadParameter("--gen and --block cannot be combined.")
    elif gen and skip_lines:
        raise click.BadParameter("--gen and --skip cannot be combined.")
    elif gen:
        # The input stream contains a single element so the expression is
        # evaluated only once.  Leverages existing eval() machinery.  Will
        # fall apart if the expression references the variable containing
        # each item.
        stream = next(pyin.evaluate(gen, [RuntimeError]))
    else:
        stream = it.chain.from_iterable(infiles)
        if not keep_input_linesep:
            stream = (i.rsplit(os.linesep, 1)[0] for i in stream)

    stream = iter(stream)
    for _ in range(skip_lines):
        try:
            next(stream)
        except StopIteration:
            raise click.ClickException("Skipped all input")

    if block:
        stream = [functools.reduce(op.iadd, stream)]

    for line in pyin.evaluate(expressions, stream):

        if isinstance(line, _compat.string_types):
            pass
        else:
            line = repr(line)

        line += join

        try:
            outfile.write(line)
        except IOError as e:
            if sys.version_info.major == 2 and 'broken pipe' in str(e).lower():
                ctx.exit()
            else:  # pragma no cover
                raise
