# -*- coding: utf-8 -*-


"""
Unittests for $ pyin
"""


import json
import os
from os import path
import textwrap

from click.testing import CliRunner
import pytest

import pyin.cli


with open(path.join('sample-data', 'csv-with-header.csv')) as f:
    CSV_WITH_HEADER = f.read()


def test_single_expr():
    result = CliRunner().invoke(pyin.cli.main, [
        "line.upper()"
    ], input=CSV_WITH_HEADER)
    assert result.exit_code == 0
    assert result.output.strip() == CSV_WITH_HEADER.upper().strip()


def test_multiple_expr():
    expected = os.linesep.join((
        '"FIELD1","FIELD2","FIELD3"',
        '["l2f1,l2f2,l2f3"]',
        '"l3f1","l3f2","l3f3"',
        '"l4f1","l4f2","l4f3"',
        'END'))
    result = CliRunner().invoke(pyin.cli.main, [
        '-i', path.join('sample-data', 'csv-with-header.csv'),
        "line.upper() if 'field' in line else line",
        "'l1' not in line",
        "line.replace('\"', '').split() if 'l2' in line else line",
        "'END' if 'l5' in line else line"
    ])
    assert result.exit_code == 0
    assert result.output.strip() == expected.strip()


def test_with_imports():
    result = CliRunner().invoke(pyin.cli.main, [
        'tests.module.upper(line)'
    ], input=CSV_WITH_HEADER)
    assert result.exit_code == 0
    assert result.output == CSV_WITH_HEADER.upper()


def test_with_generator():
    result = CliRunner().invoke(pyin.cli.main, [
        "(i for i in line)"
    ], input=CSV_WITH_HEADER)
    print(result.output)
    assert result.exit_code == 0
    assert os.linesep.join(
        [json.dumps(list((i for i in line))) for line in CSV_WITH_HEADER.splitlines()])


def test_with_blank_lines():
    result = CliRunner().invoke(pyin.cli.main, [
        'line'
    ], input="")
    assert result.exit_code == 0
    assert result.output == ''


def test_block_mode():
    text = json.dumps({k: None for k in range(10)}, indent=4)
    assert len(text.splitlines()) > 1

    result = CliRunner().invoke(pyin.cli.main, [
        "--block",
        "json.loads(line)",
        "{k: v for k, v in line.items() if int(k) in range(5)}"
    ], input=text)
    assert result.exit_code == 0

    expected = '{"3": null, "4": null, "0": null, "2": null, "1": null}'
    assert json.loads(expected) == json.loads(result.output)


def test_unicode(runner):

    text = u"""Héllö"""
    result = runner.invoke(pyin.cli.main, [
        'line.upper()'
    ], input=text)
    assert result.exit_code == 0
    assert result.output.strip() == text.strip().upper()


@pytest.mark.parametrize("skip_lines", [1, 3])
def test_skip_single_line(runner, skip_lines):
    result = runner.invoke(pyin.cli.main, [
        '--skip', skip_lines,
        'line'
    ], input=CSV_WITH_HEADER)
    assert result.exit_code == 0
    expected = os.linesep.join(CSV_WITH_HEADER.splitlines()[skip_lines:])
    assert result.output.strip() == expected.strip()


def test_skip_all_input(runner):
    result = runner.invoke(pyin.cli.main, [
        '--skip', 100,
        'line'
    ], input=CSV_WITH_HEADER)
    assert result.output != 0
    assert 'skipped' in result.output.lower()


def test_repr(runner):

    text = """
    2015-01-01
    2015-01-02
    2015-01-03
    """.strip()

    result = runner.invoke(pyin.cli.main, [
        "line.strip()",
        "datetime.datetime.strptime(line, '%Y-%m-%d')",
        "isinstance(line, datetime.datetime)"
    ], input=text)

    assert result.exit_code == 0
    assert result.output.strip() == textwrap.dedent("""
    datetime.datetime(2015, 1, 1, 0, 0)
    datetime.datetime(2015, 1, 2, 0, 0)
    datetime.datetime(2015, 1, 3, 0, 0)
    """).strip()
