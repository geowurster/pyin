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
    return os.path.join('sample-data', 'csv-with-header.csv')
