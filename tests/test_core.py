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


def test_floating_point_division():
    result = next(pyin.core.pmap('5 / 3', ['']))
    assert isinstance(result, float)
    assert 1 < result < 2


@pytest.mark.parametrize("expression", [
    'return',  # Evaluates as a statement, not string.
    ''
])
def test_invalid_expression(expression):
    with pytest.raises(SyntaxError):
        next(pyin.core.pmap(expression, []))
