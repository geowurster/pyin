"""Tests for :func:`pyin.compile`."""


import pytest

import pyin


def test_invalid_directive():

    """Catch unrecognized directives."""

    with pytest.raises(ValueError) as e:
        pyin.compile('%bad')

    assert str(e.value) == 'invalid directive: %bad'


def test_missing_argument():

    """Directive missing an argument should raise an exception."""

    with pytest.raises(ValueError) as e:
        list(pyin.eval('%eval', []))

    assert "missing argument 'expression' for directive: %eval" in str(e.value)
