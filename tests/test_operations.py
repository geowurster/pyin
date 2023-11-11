"""Tests for ``pyin`` operations for algorithmic correctness."""


import csv
import itertools as it
import json
import operator as op
import os

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
    actual = list(pyin.eval("%chain", stream))

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


def test_OpCSVDict(csv_with_header_content):

    csv_lines = [
        i.rstrip(os.linesep) for i in csv_with_header_content.splitlines()]

    row_dicts = list(pyin.eval('%csvd', csv_lines))
    assert row_dicts == list(csv.DictReader(csv_lines))

    text_rows = list(pyin.eval('%csvd', row_dicts))
    assert text_rows == csv_lines


@pytest.mark.parametrize("value,expected", [
    (['123', '456'], ['321', '654']),
    ([[1, 2], [3, 4]], [[2, 1], [4, 3]]),
    ([(1, 2), (3, 4)], [(2, 1), (4, 3)]),
    ([{'k1': 'v1', 'k2': 'v2'}], [('k2', 'k1')])
])
def test_OpRev_items(value, expected):

    """Reverse each item independently."""

    actual = list(pyin.eval('%rev', value))
    assert expected == actual


def test_OpRev_stream():

    """Reverse the entire stream."""

    actual = list(pyin.eval('%revstream', range(3)))
    assert [2, 1, 0] == actual


def test_OpBatched():

    """``%batched`` groups data properly."""

    actual = list(pyin.eval(['%batched', '2'], range(5)))
    assert [(0, 1), (2, 3), (4, )] == actual


@pytest.mark.parametrize('directive, expected', [
    ('%split', ['Word1', 'Word2']),
    ('%lower', ' word1 word2 '),
    ('%upper', ' WORD1 WORD2 '),
    ('%strip', 'Word1 Word2'),
    ('%lstrip', 'Word1 Word2 '),
    ('%rstrip', ' Word1 Word2')
])
def test_OpStrNoArgs(directive, expected):

    """Tests for ``OpStrNoArgs()``."""

    value = ' Word1 Word2 '

    actual = list(pyin.eval(directive, [value]))
    assert len(actual) == 1
    actual = actual[0]

    assert expected == actual


@pytest.mark.parametrize('directive, argument, expected', [
    ('%join', ' ', '- Word1 Word2 -'),
    ('%splits', '1', ['- Word', ' Word2 -']),
    ('%partition', 'W', ('- ', 'W', 'ord1 Word2 -')),
    ('%rpartition', 'W', ('- Word1 ', 'W', 'ord2 -')),
    ('%strips', '-', ' Word1 Word2 '),
    ('%lstrips', '-', ' Word1 Word2 -'),
    ('%rstrips', '-', '- Word1 Word2 ')
])
def test_OpStrOneArg(directive, argument, expected):

    """Tests for ``OpStrOneArg()``."""

    value = '- Word1 Word2 -'
    if directive == '%join':
        value = value.split()

    actual = list(pyin.eval([directive, argument], [value]))
    assert len(actual) == 1
    actual = actual[0]

    assert expected == actual


def test_OpReplace():

    """Tests for ``OpReplace()``."""

    value = 'word'
    expected = 'yard'

    expressions = ['%replace', 'wo', 'ya']
    actual = list(pyin.eval(expressions, [value]))
    assert len(actual) == 1
    actual = actual[0]

    assert expected == actual


@pytest.mark.parametrize("directive,value,expected", [
    ('%bool', 1, True),
    ('%bool', 0, False),
    ('%dict', [('k', 'v')], {'k': 'v'}),
    ('%float', '1', 1.0),
    ('%float', '1.2', 1.2),
    ('%int', '0', 0),
    ('%list', 'abc', ['a', 'b', 'c']),
    ('%set', 'ijk', {'i', 'j', 'k'}),
    ('%str', 1.23, '1.23'),
    ('%tuple', 'xyz', ('x', 'y', 'z'))
])
def test_OpCast(directive, value, expected):

    """Tests for ``OpCast()``."""

    if directive == '%bool':
        func = op.is_
    else:
        func = op.eq

    actual = list(pyin.eval(directive, [value]))
    assert len(actual) == 1
    actual = actual[0]

    assert func(expected, actual)


@pytest.mark.parametrize("count", [0, 1])
def test_OpISlice(count):

    """Tests for ``OpISlice()``."""

    data = range(3)
    expected = list(it.islice(data, count))
    actual = list(pyin.eval(['%islice', str(count)], data))
    assert expected == actual
