"""Tests for ``pyin`` operations for algorithmic correctness."""


import itertools as it

import pytest

import pyin


def test_accumulate():

    stream = range(3)
    expected = list(stream)
    actual = list(pyin.eval("%accumulate", stream))

    # Stream should contain only a single element
    assert len(actual) == 1
    actual = actual[0]

    assert expected == actual


def test_flatten():

    stream = [range(3)]
    expected = [0, 1, 2]
    actual = list(pyin.eval("%flatten", stream))

    assert expected == actual


@pytest.mark.parametrize("directive,expected", [
    ('%filter', None),
    ('%filterfalse', None)
])
def test_Filter(directive, expected):

    data = list(range(10))

    mapping = {'%filter': filter, '%filterfalse': it.filterfalse}
    func = mapping[directive]

    expected = list(func(lambda x: x > 5, data))
    actual = list(pyin.eval([directive, "line > 5"], data))

    assert expected == actual


def test_BaseOperation_directive_registry_conflict():

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


def test_BaseOperation_repr():

    """Check :meth:`BaseOperation.__repr__()`"""

    class Op(pyin.BaseOperation, directives=('%dir', )):
        def __call__(self, stream):
            raise NotImplementedError

    o = Op('%dir', variable='v', scope={})
    assert repr(o) == '<Op(%dir)>'


def test_BaseOperation_init_directive_mismatch():

    class Op(pyin.BaseOperation, directives=('%dir', )):
        def __call__(self, stream):
            raise NotImplementedError

    with pytest.raises(ValueError) as e:
        Op('%mismatch', variable='v', scope={})

    assert "with directive '%mismatch' but supports: %dir"
