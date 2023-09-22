"""Tests for ``pyin`` operations for algorithmic correctness."""


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
