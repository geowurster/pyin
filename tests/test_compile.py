"""Tests for :func:`pyin.compile`."""


import pytest

import pyin


def test_invalid_directive():

    """Catch unrecognized directives."""

    with pytest.raises(ValueError) as e:
        pyin.compile('%bad')

    assert str(e.value) == 'invalid directive: %bad'
