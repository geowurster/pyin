"""pytest fixtures"""


from click.testing import CliRunner
import pytest


@pytest.fixture(scope='module')
def runner():
    return CliRunner()
