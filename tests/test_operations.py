"""Tests for ``pyin`` operations for algorithmic correctness."""


import itertools as it
import json

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
    actual = list(pyin.eval([directive, "i > 5"], data))

    assert expected == actual


def test_OpBase_directive_registry_conflict():

    """Two operations register the same directive."""

    class Op1(pyin.OpBase, directives=('%dir', )):
        pass

    with pytest.raises(RuntimeError) as e:

        # The test lives in 'OpBase.__init_subclass__()', so the class
        # cannot even be defined.
        class Op2(pyin.OpBase, directives=('%dir', )):
            pass

    assert "directive '%dir' conflict" in str(e.value)
    assert 'Op1' in str(e.value)
    assert 'Op2' in str(e.value)


def test_OpBase_repr():

    """Check :meth:`OpBase.__repr__()`"""

    class Op(pyin.OpBase, directives=('%dir', )):
        def __call__(self, stream):
            raise NotImplementedError

    o = Op('%dir', variable='v', stream_variable='stream', scope={})
    assert repr(o) == '<Op(%dir)>'


def test_OpBase_init_directive_mismatch():

    class Op(pyin.OpBase, directives=('%dir', )):
        def __call__(self, stream):
            raise NotImplementedError

    with pytest.raises(ValueError) as e:
        Op('%mismatch', variable='v', stream_variable='stream', scope={})

    assert "with directive '%mismatch' but supports: %dir" in str(e.value)


def test_Eval_syntax_error():

    """Produce a helpful error when encountering :obj:`SyntaxError`.

    :obj:`pyin.Eval` compiles Python expressions to code objects, which can
    hit a :obj:`SyntaxError`. Be sure that this is translated to a helpful
    error for the caller.
    """

    expr = '$ syntax error $'
    with pytest.raises(SyntaxError) as e:
        list(pyin.eval(expr, range(1)))

    assert 'contains a syntax error' in str(e.value)
    assert expr in str(e.value)


def test_OpJSON():

    """``%json`` encodes and decodes."""

    python_objects = [list(range(3)) for _ in range(3)]
    json_strings = [json.dumps(i) for i in python_objects]

    # Object -> JSON string
    actual = list(pyin.eval('%json', python_objects))
    assert json_strings == actual

    # JSON string -> object
    actual = list(pyin.eval('%json', actual))
    assert python_objects == actual


def test_OpStream():

    """``%stream`` operates on the stream itself and not a single item."""

    expressions = ['%stream', '[i * 10 for i in stream]']
    actual = list(pyin.eval(expressions, range(3)))

    assert [0, 10, 20] == actual
