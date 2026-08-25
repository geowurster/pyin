"""Tests for :func:`pyin.compile`."""


import pytest

import pyin


def test_compile():

    """Compile multiple expressions."""

    compiled = pyin.compile(('i', '%json'))

    assert len(compiled) == 2
    assert isinstance(compiled[0], pyin.DirectiveEval)
    assert isinstance(compiled[1], pyin.DirectiveJSON)


def test_compile_single():

    """Compile a single expression."""

    compiled = pyin.compile('%json')

    assert len(compiled) == 1
    assert isinstance(compiled[0], pyin.DirectiveJSON)


def test_invalid_directive():

    """Catch unrecognized directives."""

    with pytest.raises(pyin.DirectiveError) as e:
        pyin.compile('%bad')

    assert str(e.value) == 'invalid directive: %bad'


def test_missing_argument():

    """Directive missing an argument should raise an exception."""

    with pytest.raises(pyin.DirectiveError) as e:
        list(pyin.eval('%eval', []))

    assert "missing argument 'expression' for: %eval" in str(e.value)
