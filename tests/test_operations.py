"""Tests for ``pyin`` operations for algorithmic correctness.

When adding a new test, check first if it can be included in:

1. ``test_simple_item()`` - Single input/output element and no arguments.
2. ``test_simple_item_args()`` - Above but requires arguments.
3. ``test_simple_stream()`` - Shape of stream. Arguments optional.
"""


import csv
import os

import pytest

import pyin


@pytest.mark.parametrize("directive, item, expected", [

    # %json
    ('%json', '[0, 1, 2]', [0, 1, 2]),
    ('%json', [0, 1, 2], '[0, 1, 2]'),

    # %rev
    ('%rev', 'abc', 'cba'),
    ('%rev', [1, 2], [2, 1]),
    ('%rev', (3, 4), (4, 3)),
    ('%rev', {'k1': 'v1', 'k2': 'v2'}, ('k2', 'k1')),

    # Simple type casting
    ('%bool', 1, True),
    ('%bool', 0, False),
    ('%dict', [('k', 'v')], {'k': 'v'}),
    ('%float', '1', 1.0),
    ('%float', '1.2', 1.2),
    ('%int', '0', 0),
    ('%list', 'abc', ['a', 'b', 'c']),
    ('%set', 'ijk', {'i', 'j', 'k'}),
    ('%str', 1.23, '1.23'),
    ('%tuple', 'xyz', ('x', 'y', 'z')),

    # 'str' methods
    ('%split', ' Word1 Word2 ', ['Word1', 'Word2']),
    ('%lower', ' Word1 Word2 ', ' word1 word2 '),
    ('%upper', ' Word1 Word2 ', ' WORD1 WORD2 '),
    ('%strip', ' Word1 Word2 ', 'Word1 Word2'),
    ('%lstrip', ' Word1 Word2 ', 'Word1 Word2 '),
    ('%rstrip', ' Word1 Word2 ', ' Word1 Word2')

])
def test_simple_item(directive, item, expected):

    """Simple item tests.

    A test should be included here if it:

    1. Compares a single input to a single output value.
    2. Requires no arguments.

    See ``test_simple_item_args()`` if arguments are required, and
    ``test_simple_stream()`` if the test is higher-level and focusing on the
    shape of the stream.
    """

    actual = list(pyin.eval(directive, [item]))

    # Only want to look at the first element
    assert len(actual) == 1
    assert actual[0] == expected


@pytest.mark.parametrize("directive, args, data, expected", [
    ('%replace', ('wo', 'ya'), 'word', 'yard'),
    ('%splits', ('ab', ), 'abc', ['', 'c']),
    ('%partition', ('bb', ), 'abbabba', ('a', 'bb', 'abba')),
    ('%rpartition', ('bb', ), 'abbabba', ('abba', 'bb', 'a')),
    ('%strips', ('ab', ), 'abcba', 'c'),
    ('%lstrips', ('ab', ), 'abcba', 'cba'),
    ('%rstrips', ('ab', ), 'abcba', 'abc'),
    ('%join', ('-', ), ['a', 'b'], 'a-b'),
])
def test_simple_item_args(directive, args, data, expected):

    """Simple tests requiring one or more arguments.

    Like ``test_simple_item()``, but with arguments. See also
    ``test_simple_item()``, and ``test_simple_stream()``.
    """

    expressions = [directive, *args]
    actual = list(pyin.eval(expressions, [data]))

    assert len(actual) == 1
    assert actual[0] == expected


@pytest.mark.parametrize("directive, args, stream, expected", [

    # No arguments
    ('%accumulate', (), range(3), [[0, 1, 2]]),
    ('%chain', (), [range(3)], [0, 1, 2]),
    ('%revstream', (), range(3), [2, 1, 0]),

    # One argument
    ('%filter', ('None', ), range(3), [1, 2]),
    ('%filterfalse', ('None', ), range(3), [0]),
    ('%filter', ('i >= 2', ), range(5), [2, 3, 4]),
    ('%filterfalse', ('i >= 2', ), range(5), [0, 1]),
    ('%stream', ('[i * 10 for i in stream]', ), range(3), [0, 10, 20]),
    ('%batched', ('2', ), range(5), [(0, 1), (2, 3), (4, )]),
    ('%islice', ('0', ), range(3), []),
    ('%islice', ('1', ), range(3), [0]),

])
def test_simple_stream(directive, args, stream, expected):

    """Simple stream tests.

    Adjusting the structure of the stream. See also ``test_simple_item()``, and
    ``test_simple_item_args()``.
    """

    expressions = [directive, *args]

    actual = list(pyin.eval(expressions, stream))
    assert actual == expected


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


def test_OpCSVDict(csv_with_header_content):

    csv_lines = [
        i.rstrip(os.linesep) for i in csv_with_header_content.splitlines()]

    row_dicts = list(pyin.eval('%csvd', csv_lines))
    assert row_dicts == list(csv.DictReader(csv_lines))

    text_rows = list(pyin.eval('%csvd', row_dicts))
    assert text_rows == csv_lines
