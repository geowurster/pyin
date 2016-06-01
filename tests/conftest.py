"""
pytest fixtures
"""


import os.path

from click.testing import CliRunner
import pytest


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
