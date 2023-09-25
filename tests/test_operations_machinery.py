"""Tests for making :mod:`pyin` operations work.

Registration, how information about the parent scope is passed around, etc.
"""


import pytest

import pyin


def test_directive_registry_conflict():

    """Two operations register the same directive."""

    class Op1(pyin.BaseOperation, directives=('%dir', )):
        pass

    with pytest.raises(RuntimeError) as e:

        # The test lives in 'BaseOperation.__init_subclass__()', so the class
        # cannot even be defined.
        class Op2(pyin.BaseOperation, directives=('%dir', )):
            pass

    assert "directive '%dir' conflict" in str(e.value)
    assert 'Op1' in str(e.value)
    assert 'Op2' in str(e.value)
