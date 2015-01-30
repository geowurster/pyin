"""
Perform Python operations on every line read from stdin
"""


import os
import sys

import click


def pyin(stream, operation, strip=True):

    for line in stream:
        if strip:
            line = line.strip()
        yield eval(operation)


@click.command()
@click.option(
    '-i', '--i-stream', metavar='STDIN', type=click.File(mode='r'), default=sys.stdin,
    help="Input stream"
)
@click.option(
    '-o', '--o-stream', metavar='FILE', type=click.File(mode='w'), default=sys.stdout,
    help="Output stream"
)
@click.option(
    '-s / -ns', '--strip / --no-strip', is_flag=True, default=True,
    help="Don't strip leading and trailing whitespace"
)
@click.option(
    '-n', '--newline', metavar='CHAR', default=os.linesep,
    help="Newline character to append to every line"
)
@click.argument(
    'operation', type=click.STRING, required=True
)
def main(i_stream, operation, o_stream, strip, newline):

    try:
        for output in pyin(i_stream, operation, strip=strip):
            o_stream.write(str(output) + newline)
        sys.exit(0)

    except Exception as e:
        click.echo(e.message, err=True)
        sys.exit(1)
