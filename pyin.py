import sys

import click


def pyin(stream, operation):

    for line in stream:
        yield eval(operation)


@click.command()
@click.option(
    '-i', '--i-stream', metavar='STDIN', type=click.File(mode='r'), default=sys.stdin,
    help="Input stream"
)
@click.option(
    '-o', '--o-stream', metavar='STDOUT', type=click.File(mode='w'), default=sys.stdout,
    help="Output stream"
)
@click.argument(
    'operation', type=click.STRING, required=True
)
def main(i_stream, operation, o_stream):

    try:
        for output in pyin(i_stream, operation):
            o_stream.write(str(output))
        sys.exit(0)

    except Exception as e:
        click.echo(e.message, err=True)
        sys.exit(1)
