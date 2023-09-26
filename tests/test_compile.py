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


def test_missing_annotation():

    """Directives with missing arg type annotations should raise an exception.
    """

    class OpBroken(pyin.OpBase, directives=('%broken', )):

        def __init__(self, directive: str, arg, /, **kwargs):
            super().__init__(directive, **kwargs)
            self.arg = arg

        def __call__(self, stream):
            return stream

    with pytest.raises(RuntimeError) as e:
        list(pyin.eval(['%broken', 'value'], []))

    assert 'missing a type annotation' in str(e.value)
    assert "argument 'arg'" in str(e.value)
    assert "directive '%broken'" in str(e.value)
