"""
Unittests for: pyin.core
"""


import sys

import pytest

import pyin.core
import tests._test_module


def test_single_expr():
    result = list(pyin.core.pmap("20 <= line <= 80", range(100)))
    assert len(result) == len(list(range(20, 81)))
    for item in result:
        assert 20 <= item <= 80


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 3),
    reason="Importing in early versions of Python3 is different?")
def test_importer():
    out = pyin.core._importer('tests._test_module.function', {})
    assert out == {'tests': tests}
    assert out['tests']._test_module.upper('word') == 'WORD'


def test_with_map():
    result = list(pyin.core.pmap(
        "list(map(int, line.split('-')))", ['2015-01-01']))
    assert result == [[2015, 1, 1]]


@pytest.mark.parametrize("obj", [
    'map', 'reduce', 'op', 'it'
])
def test_scope(obj):
    """Make sure specific objects aren't removed from the scope."""
    for res in pyin.core.pmap(obj, 'word'):
        pass
