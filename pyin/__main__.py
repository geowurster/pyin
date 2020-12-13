"""``pyin``'s commandline interface."""


from __future__ import print_function

import argparse
import errno
import os
import sys

from pyin import _compat, evaluate, generate, expressions
from pyin.exceptions import CLIError, CompileError, EvaluateError


__all__ = ['parser', 'main']


def _type_var(value):

    """Ensure a value can be used as a variable name in the expression scope.

    Raises
    ======
    argparse.ArgumentTypeError
        If value is a reserved keyword or

    Returns
    =======
    str
        Input ``value``.
    """

    try:
        eval(value, {}, {})
        exc_info = None
    # SyntaxError cannot be caught directly
    except SyntaxError:
        exc_info = sys.exc_info()
    except NameError:
        return value

    if exc_info is not None:
        raise argparse.ArgumentTypeError(
            "value cannot be used as a variable: {}".format(value))


def parser():

    """The argument parser used by the commandline interface.

    Returns
    =======
    argparse.ArgumentParser
    """

    p = argparse.ArgumentParser(
        prog='pyin',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Reading
    input_group = p.add_mutually_exclusive_group()
    input_group.add_argument(
        '--gen', metavar='EXPR', dest='generate_expr',
        help="Execute expression and feed results into other expressions.")
    input_group.add_argument(
        '-i', '--infile', type=argparse.FileType('r'), default='-',
        help="Read input from this file.")

    # Pre-processing
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        '-b', '--block', action='store_true',
        help="Pass entire input file to expressions as a single block"
             " of data. When an input file is given the entire file is read,"
             " an when '--gen' is given then all input is stored in a list.")
    group.add_argument(
        '--skip', default=0, type=int,
        help="Skip N lines before evaluating expressions.")

    # Processing
    p.add_argument(
        'expressions', nargs='*',
        help="Process input data with these expressions.")
    p.add_argument(
        '-v', '--var', default=expressions._DEFAULT_VARIABLE, dest='variable',
        type=_type_var,
        help="Store data in this variable.")

    # Post-processing and writing
    p.add_argument(
        '--join', '--linesep', type=str, default=os.linesep,
        help="Print this sequence after every line of output text.")
    p.add_argument(
        '-o', '--outfile', type=argparse.FileType('w'), default='-',
        help="Write output to this file.")

    return p


def main(
        infile, outfile, expressions, block, skip, variable, generate_expr, join):

    """``pyin``'s commandline interface. See arguments defined in ``parser``
    for more information.

        namespace = paser().parse_args()
        exit_code = main(**vars(namespace))

    Raises
    ======
    CLIError
        Commandline interface problem.
    CompileError
        Could not compile an expression.
    EvaluateError
        Could not evaluate an expression.

    Returns
    =======
    int
        Exit code.
    """

    # Cannot fully validate this in the parser without having to deal with
    # opening the file.
    if generate_expr is not None and not infile.isatty():
        raise argparse.ArgumentError(
            None, "cannot combine '--gen' with piping data to stdin")

    # Generating data for input. Must also handle '--block'.
    elif generate_expr is not None:
        stream = generate(generate_expr)
        if block:
            stream = [stream]
        elif not isinstance(stream, _compat.Iterable):
            raise EvaluateError(
                "expression failed to generate an iterable object: {}".format(
                    generate_expr))
    elif block:
        stream = (i for i in [infile.read()])
    else:
        stream = (l.rstrip(os.linesep) for l in infile)
        if skip > 0:
            for _ in range(skip):
                try:
                    next(stream)
                except StopIteration:
                    break

    # pyin can be used to generate data on the command line with:
    #   $ pyin --gen "range(10)" "i"
    # but this bit below eliminates the required "i".
    if not expressions:
        expressions = ["{}".format(variable)]

    try:
        results = evaluate(expressions, stream, variable=variable)
        for idx, line in enumerate(results):

            if not isinstance(line, _compat.string_types):
                line = repr(line)

            # Write line and optional newline, but avoid a string copy.
            outfile.write(line)
            if not line.endswith(join):
                outfile.write(join)

        outfile.flush()

    except OSError as e:
        if e.errno == errno.EPIPE:
            # Python flushes standard streams on exit; redirect remaining output
            # to devnull to avoid another BrokenPipeError at shutdown
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            return 1
        else:
            _compat.reraise(e.__class__, e, sys.exc_info()[2])


def cli_entrypoint():
    p = parser()
    ns = p.parse_args()

    try:
        ecode = main(**vars(ns))
    except argparse.ArgumentError as e:
        if 'interactive stdin' in e.message:
            p.print_usage()
            exit()
        else:
            p.error(e.message)
    except (CLIError, CompileError, EvaluateError) as e:
        ecode = 1
        print("ERROR: {}".format(e), file=sys.stderr)
    exit(ecode)


if __name__ == "__main__":
    cli_entrypoint()
