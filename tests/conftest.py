"""``pytest`` fixtures.

Previously the CLI was powered by ``click``, but the dependency was removed
in favor of relying only on the ``stdlib``. The CLI was extensively tested
using ``click.testing.CliRunner()``, so rather than rework the tests,
:obj:`PyinCliRunner` was developed as a drop-in replacement for our very
specific use of the former.

Typically, a ``pytest`` using ``CliRunner()`` would look like:

.. code-block:: python

    import click
    from click.testing import CliRunner


    @click.command()
    @click.argument('arg')
    @click.option('--option')
    def func(arg, option):
        click.echo(f"{arg} {option}")


    def test_func():

        expected = 'arg option'

        runner = CliRunner()
        result = runner.invoke(func, ['arg', '--option', 'option'])

        assert result.exit_code == 0
        assert expected == result.output.strip()

However, our tests pre-instantiate an instance of the class and receive it via
a ``pytest`` fixture. In reality our use is more like this:

.. code-block::

    @pytest.fixture(scope='function')
    def runner():
        return CliRunner()


    def test_func(runner):

        expected = 'arg option'

        result = runner.invoke(func, ['arg', '--option', 'option'])

        assert result.exit_code == 0
        assert expected == result.output.strip()

So, :obj:`PyinCliRunner` matches exactly these API calls, albeit in a different
way. The result is the same, and the mechanics are roughly the same. Do not
hesitate to remove or refactor this class if needed. It is strictly vestigial
and emerged out of the path of least resistance.
"""


from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import os.path
from types import MethodType
from typing import Callable
from unittest import mock

import pytest


@pytest.fixture(scope='function')
def runner():
    return PyinCliRunner


@pytest.fixture(scope='module')
def path_csv_with_header():
    return os.path.join('tests', 'data', 'csv-with-header.csv')


@pytest.fixture(scope='module')
def csv_with_header_content(path_csv_with_header):
    with open(path_csv_with_header) as f:
        return f.read()


class PyinCliRunner:

    """Kind of like ``click.testing.CliRunner()``.

    A sort of drop-in replacement for our use of ``CliRunner()`` to avoid some
    more disruptive changes. It doesn't match the ``CliRunner()`` API so much
    as it matches the way that class is invoked in some tests.

    In addition to ``CliRunner()``, click also has a ``Result()`` object for
    storing the results of a given CLI run. This class merges the two together.
    Normally ``CliRunner()`` is instantiated with environment settings and
    other configuration, but this class is intended to only be instantiated
    through the :meth:`~invoke` method, which sets information about a CLI
    run on this class when it is instantiated. I know. Pretty weird. Again,
    it matches existing _code_, not the API. We're trying to minimize the diff
    and match existing patterns, not make a complicated thing.

    As with ``CliRunner()``, this class captures ``stderr`` and ``stdoutt``.
    """

    def __init__(self, *, exit_code: int, output: str, err: str):

        """
        :param exit_code:
            Program exit code.
        :param output:
            Contents of ``stdout``.
        :param err:
            Contents of ``stderr``.
        """

        self.exit_code = exit_code
        self.output = output
        self.err = err

    @classmethod
    def invoke(
            cls,
            func: Callable,
            rawargs: list,
            *,
            input: str | None = None
    ) -> "CliRunner":

        """Execute a command and return the result.

        :param func:
            Execute this function.
        :param rawargs:
            A list of unparsed arguments. Like :obj:`sys.argv` but without
            the interpreter path.
        :param input:
            Replace :obj:`sys.stdin` with a :obj:`io.StringIO` instance
            containing this data. Note that the mocked :meth:`sys.stdin.isatty`
            is also mocked to report ``False`` in this case.
        """

        if not all(isinstance(i, str) for i in rawargs):
            raise RuntimeError(
                f"one or more arguments is not a str: {rawargs}")

        stdin = StringIO(input)
        stderr = StringIO()
        stdout = StringIO()

        # When passing data to place in 'stdin', be sure to mock
        # 'sys.stdin.isatty()' properly. Even piping an empty string to a
        # processing counts as a non-interactive session, as evidenced by
        # this reporting 'False':
        #   echo "" | python -c "import sys; print(sys.stdin.isatty())"
        if input is None:
            isatty = True
        else:
            isatty = False
        stdin.isatty = MethodType(lambda self: isatty, stdin)

        with ExitStack() as stack:

            stack.enter_context(mock.patch('sys.stdin', new=stdin))
            stack.enter_context(redirect_stderr(stderr))
            stack.enter_context(redirect_stdout(stdout))

            try:
                func(rawargs)
            except SystemExit as e:
                exit_code = e.code

        if not isinstance(exit_code, int):
            raise RuntimeError(f"exit code is not an integer: {exit_code}")

        stderr.seek(0)
        stdout.seek(0)

        return cls(
            exit_code=exit_code,
            output=stdout.read(),
            err=stderr.read()
        )
