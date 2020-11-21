"""
pytest fixtures
"""


from collections import namedtuple
import os.path
import subprocess

import pytest

from pyin._compat import ensure_binary, ensure_text


class CliRunner(object):

    def invoke(self, args, input=None):

        proc = subprocess.Popen(
            ['pyin'] + list(args),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)

        if input is not None:
            input = ensure_binary(input)

        stdout, _ = proc.communicate(input=input)

        cli_result = namedtuple("CliResult", ('output', 'exit_code'))

        return cli_result(
            ensure_text(stdout),
            proc.returncode)


@pytest.fixture(scope='module')
def runner():
    return CliRunner()


@pytest.fixture(scope='module')
def path_csv_with_header():
    return os.path.join('tests', 'data', 'csv-with-header.csv')


@pytest.fixture(scope='module')
def csv_with_header_content(path_csv_with_header):
    with open(path_csv_with_header) as f:
        return f.read()
