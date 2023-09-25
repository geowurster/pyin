"""Tests for :func:`test_normalize_expressions`."""


import pytest

import pyin


@pytest.mark.parametrize('wrap', [True, False])
def test_normalize_expressions(wrap):

    """:func:`_normalize_expressions` decorator adjusts arguments."""

    @pyin._normalize_expressions
    def func(expressions):
        return expressions

    expr = 'expr'
    if wrap:
        expr = [expr]

    result = func(expr)
    assert result == ('expr', )


@pytest.mark.parametrize('wrap', [True, False])
def test_normalize_expressions_not_a_sequence(wrap):

    """Passing expressions that are not a sequence raises an exception."""

    @pyin._normalize_expressions
    def func(expressions):
        return expressions

    with pytest.raises(TypeError) as e:
        func(1)

    assert 'not a sequence' in str(e.value)
