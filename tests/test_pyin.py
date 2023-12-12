"""Tests for ``$ pyin`` command line interface."""


import inspect
from io import StringIO
import json
import os
import pty
import signal
import subprocess
import sys
import textwrap
import time

import pytest

import pyin
from pyin import _cli_entrypoint


def test_single_expr(runner, csv_with_header):
    result = runner.invoke(_cli_entrypoint, [
        "i.upper()"
    ], input=csv_with_header)
    assert result.exit_code == 0
    assert not result.err
    assert result.output.strip() == csv_with_header.upper().strip()


def test_multiple_expr(runner, csv_with_header, tmp_path):

    csv_path = tmp_path / "test_multiple_expr.csv"

    with open(csv_path, 'w') as f:
        f.write(csv_with_header)

    expected = os.linesep.join((
        '"FIELD1","FIELD2","FIELD3"',
        "['l2f1,l2f2,l2f3']",
        '"l3f1","l3f2","l3f3"',
        '"l4f1","l4f2","l4f3"',
        'END'))
    result = runner.invoke(_cli_entrypoint, [
        '-i', str(csv_path),
        "i.upper() if 'field' in i else i",
        "%filter", "'l1' not in i",
        "i.replace('\"', '').split() if 'l2' in i else i",
        "'END' if 'l5' in i else i"
    ])
    assert result.exit_code == 0
    assert not result.err
    assert result.output.strip() == expected.strip()


def test_with_blank_lines(runner):
    result = runner.invoke(_cli_entrypoint, [
        'i'
    ], input="")
    assert result.exit_code == 0
    assert not result.err
    assert result.output == ''


def test_repr(runner):

    text = """
    2015-01-01
    2015-01-02
    2015-01-03
    """.strip()

    result = runner.invoke(_cli_entrypoint, [
        "i.strip()",
        "datetime.datetime.strptime(i, '%Y-%m-%d')",
        "%filter", "isinstance(i, datetime.datetime)"
    ], input=text)

    assert result.exit_code == 0
    assert not result.err
    assert result.output.strip() == textwrap.dedent("""
    datetime.datetime(2015, 1, 1, 0, 0)
    datetime.datetime(2015, 1, 2, 0, 0)
    datetime.datetime(2015, 1, 3, 0, 0)
    """).strip()


@pytest.mark.parametrize('gen_expr,expected', [
    ('range(3)', os.linesep.join(['1', '2', '3']) + os.linesep),
    ('[]', '')
])
def test_gen(gen_expr, expected, runner):

    """``--gen`` to generate input."""

    result = runner.invoke(_cli_entrypoint, ['--gen', gen_expr, "i + 1"])

    assert result.exit_code == 0
    assert not result.err
    assert expected == result.output


def test_gen_stdin(runner):

    """``--gen`` combined with piping data to ``stdin`` is not allowed."""

    result = runner.invoke(_cli_entrypoint, ['--gen', 'range(3)'], input="trash")

    assert result.exit_code == 2
    assert not result.output
    for item in ('cannot combine', '--gen', 'stdin'):
        assert item in result.err


def test_gen_not_iterable(runner):

    """``--gen`` does not produce an iterable object."""

    result = runner.invoke(_cli_entrypoint, ['--gen', '1'])

    assert result.exit_code == 1
    assert not result.output
    for item in ('--gen', 'iterable object'):
        assert item in result.err


def test_bad_directive(runner):

    """Catch bad directives."""

    result = runner.invoke(_cli_entrypoint, ['--gen', 'range(1)', '%bad'])

    assert result.exit_code == 1
    assert not result.output
    assert result.err == 'ERROR: invalid directive: %bad' + os.linesep


def test_no_arguments_prints_help(runner):

    """Invoking ``$ pyin`` without any arguments or ``stdin`` prints help."""

    result = runner.invoke(_cli_entrypoint, [])

    with StringIO() as f:
        pyin.argparse_parser().print_help(file=f)
        f.seek(0)
        expected = f.read()

    assert result.exit_code == 2
    assert not result.err
    assert expected == result.output


def test_KeyboardInterrupt():

    """:obj:`KeyboardInterrupt` handling.

    Notice that this test is slightly slower than the rest? That's because
    it must :func:`time.sleep` briefly.
    """

    # It is not possible to test this with 'threading.Thread()' or
    # 'multiprocessing.Process()'. Signals are always handled by Python's
    # main thread, so it is not possible really feasible to get the signal
    # into a thread where '_cli_entrypoint()' is running. It probably is
    # possible with some awful hackery though.

    _, fd = pty.openpty()

    proc = subprocess.Popen(
        ['pyin', '--gen', 'range(10)', '(time.sleep(0.5), i)[1]'],
        stdin=fd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    with proc as proc:

        # Sleep long enough for things to hit the main loop, otherwise we may
        # kill the process before it enters the right context.
        time.sleep(0.5)

        # Send SIGINT into the process.
        proc.send_signal(signal.SIGINT)

        # Wait for it to shut down, which should not take long at all.
        proc.wait(1)

        assert proc.returncode == 130
        assert not proc.stderr.read()


def test_main_sys_path(runner):

    """:func:`pytest.main` adjusts :attr:`sys.path`."""

    assert '' not in sys.path

    result = runner.invoke(
        _cli_entrypoint,
        ['--gen', 'range(1)', 'sys.path', 'json.dumps(i)']
    )

    assert '' not in sys.path
    assert result.exit_code == 0
    assert not result.err

    data = json.loads(result.output)
    assert '' in data

    # Ensure that 'pyin.eval()' was not in fact the thing modifying 'sys.path'
    results = list(pyin.eval('sys.path', range(1)))
    assert '' not in results[0]


def test_import_from_file_in_current_directory(runner):

    tmpname = 'relmod.py'

    def func(item):
        """Call 'item.upper()'"""
        return item.upper()

    try:

        # Create
        with open(tmpname, 'w') as f:
            f.write("# Part of: test_import_from_file_in_current_directory")
            f.write(os.linesep * 2)
            f.write(textwrap.dedent(inspect.getsource(func)))

        result = runner.invoke(
            _cli_entrypoint,
            ['--gen', "['word']", 'relmod.func(i)']
        )

        assert result.exit_code == 0, result.err
        assert not result.err
        assert result.output == 'WORD' + os.linesep

    finally:
        os.unlink(tmpname)


@pytest.mark.parametrize("linesep,expected", [
    (os.linesep, os.linesep.join('012') + os.linesep),
    ('', '012'),
    ('ab', '0ab1ab2ab')
])
def test_linesep(runner, linesep, expected):

    """``--linesep`` controls the character(s) written after every line."""

    result = runner.invoke(
        _cli_entrypoint,
        ['--gen', 'range(3)', '--linesep', linesep])

    assert result.exit_code == 0
    assert not result.err
    assert expected == result.output


def test_variable(runner):

    """Flags for altering variable names in the ``eval()`` scope."""

    result = runner.invoke(
        _cli_entrypoint,
        [
            '--gen', 'range(3)',
            '--variable', 'v', '--stream-variable', 's2',
            'v + 1',
            '%stream', '[i ** 2 for i in s2]'
        ]
    )

    assert result.exit_code == 0, result.err
    assert not result.err
    assert result.output == os.linesep.join('149') + os.linesep


@pytest.mark.parametrize("flag", ("--variable", "--stream-variable"))
def test_variable_invalid(runner, flag):

    """Ensure string passed to ``--variable`` can be used as a variable."""

    result = runner.invoke(
        _cli_entrypoint,
        [flag, '1']
    )

    assert result.exit_code == 2
    assert not result.output
    assert 'string is not valid as a variable: 1' in result.err


def test_setup(runner):

    """Test environment setup."""

    result = runner.invoke(_cli_entrypoint, [
        '--gen', 'range(1)',
        '-s', 'import itertools as itertest',
        'itertest.__name__'
    ])

    assert result.exit_code == 0
    assert not result.err
    assert result.output == 'itertools' + os.linesep


def test_setup_syntax_error(runner):

    """``SyntaxError`` in a setup statement."""

    statement = '1 invalid syntax'
    expected = f'ERROR: setup statement contains a syntax error: {statement}'

    result = runner.invoke(_cli_entrypoint, [
        '--gen', 'range(1)',
        '-s', statement
    ])

    assert result.exit_code == 1
    assert not result.output
    assert result.err == expected + os.linesep
