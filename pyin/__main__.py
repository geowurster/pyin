"""Command line interface for ``pyin``."""


import argparse
import json
import itertools as it
import os
from typing import Optional, TextIO

import pyin
import pyin.core


DESCRIPTION = r"""
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


def parser() -> argparse.ArgumentParser:

    """Construct an :obj:`argparse.ArgumentParser`.

    Provided as an entrypoint to argument parsing that can provide a better
    entrypoint to :func:`main` from Python.
    """

    aparser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    aparser.add_argument(
        '--version', action='version', version=pyin.__version__
    )
    aparser.add_argument(
        '-i', '--infile', dest='infiles', metavar='PATH',
        type=argparse.FileType('r'), default=[argparse.FileType('r')('-')],
        action='append',
        help="Input text file. Use '-' for stdin. Can be used multiple times"
             " to specify multiple input files, which is like: $ cat * | pyin"
    )
    aparser.add_argument(
        '-o', '--outfile', metavar='PATH',
        type=argparse.FileType('w'), default='-',
        help="Output text file. Use '-' for stdout."
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
        infiles: list[TextIO],
        outfile: TextIO,
        expressions: list[str],
        no_newline: bool,
        block: bool,
        skip_lines: int
) -> int:

    """Command line interface.

    Direct access to the CLI logic. :obj:`argparse.ArgumentParser` can be
    accessed with :func:`parser`.

    :param infiles:
        List of input files to read from. Files are concatenated before
        processing.
    :param outfile:
        Write output to this file.
    :param expressions:
        Evaluate these ``pyin`` expressions on each line of text from
        ``infiles``.
    :param no_newline:
        Do not append a line separator to the end of each line.
    :param block:
        Treat all input lines as a single line of text. Equivalent to reading
        all input data into a single :obj:`str` and running that through
        ``expressions``.
    :param skip_lines:
        Skip the first N lines. Applied to ``infiles`` _after_ they have
        been concatenated. Does not skip the first N lines of each file
        independently.

    :returns:
        Exit code.
    """

    input_stream = it.chain.from_iterable(infiles)

    for _ in range(skip_lines):
        try:
            next(input_stream)
        except StopIteration:
            return 0

    if block:
        iterable = [os.linesep.join((f.read() for f in infiles))]
    else:
        iterable = (l.rstrip(os.linesep) for l in input_stream)

    for line in pyin.core.pmap(expressions, iterable):

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

    args = parser().parse_args(args=rawargs)

    exit(main(**vars(args)))


if __name__ == '__main__':
    _cli_entrypoint()
