"""Tests for ``pyin.expressions``"""


import pytest

import pyin
from pyin.exceptions import CompileError


def test_single_expr():
    result = list(pyin.evaluate(["%filter", "20 <= i <= 80"], range(100)))
    assert len(result) == len(list(range(20, 81)))
    for item in result:
        assert 20 <= item <= 80


def test_with_map():
    result = list(pyin.evaluate(
        "list(map(int, i.split('-')))", ['2015-01-01']))
    assert result == [[2015, 1, 1]]


@pytest.mark.parametrize("obj", [
    'map', 'reduce', 'op', 'it'
])
def test_scope(obj):
    """Make sure specific objects aren't removed from the scope."""
    for res in pyin.evaluate(obj, 'word'):
        pass


def test_floating_point_division():
    result = next(pyin.evaluate('5 / 3', ['']))
    assert isinstance(result, float)
    assert 1 < result < 2


@pytest.mark.parametrize("expression", [
    'return',  # Evaluates as a statement, not string.
    ''
])
def test_invalid_expression(expression):
    with pytest.raises(CompileError):
        next(pyin.evaluate(expression, []))
