# -*- coding: utf-8 -*-


"""
Unittests for $ pyin
"""


import json
import os
import subprocess
import sys
import textwrap

import pytest

import pyin.cli


def test_single_expr(runner, csv_with_header_content):
    result = runner.invoke(pyin.cli.main, [
        "line.upper()"
    ], input=csv_with_header_content)
    assert result.exit_code == 0
    assert result.output.strip() == csv_with_header_content.upper().strip()


def test_multiple_expr(runner, path_csv_with_header):
    expected = os.linesep.join((
        '"FIELD1","FIELD2","FIELD3"',
        '["l2f1,l2f2,l2f3"]',
        '"l3f1","l3f2","l3f3"',
        '"l4f1","l4f2","l4f3"',
        'END'))
    result = runner.invoke(pyin.cli.main, [
        '-i', path_csv_with_header,
        "line.upper() if 'field' in line else line",
        "'l1' not in line",
        "line.replace('\"', '').split() if 'l2' in line else line",
        "'END' if 'l5' in line else line"
    ])
    assert result.exit_code == 0
    assert result.output.strip() == expected.strip()


def test_with_generator(runner, csv_with_header_content):
    result = runner.invoke(pyin.cli.main, [
        "(i for i in line)"
    ], input=csv_with_header_content)
    assert result.exit_code == 0
    assert os.linesep.join(
        [json.dumps(list((i for i in line))) for line in csv_with_header_content.splitlines()])


def test_with_blank_lines(runner):
    result = runner.invoke(pyin.cli.main, [
        'line'
    ], input="")
    assert result.exit_code == 0
    assert result.output == ''


def test_block_mode(runner):
    text = json.dumps({k: None for k in range(10)}, indent=4)
    assert len(text.splitlines()) > 1

    result = runner.invoke(pyin.cli.main, [
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
def test_skip_single_line(runner, skip_lines, csv_with_header_content):
    result = runner.invoke(pyin.cli.main, [
        '--skip', skip_lines,
        'line'
    ], input=csv_with_header_content)
    assert result.exit_code == 0
    expected = os.linesep.join(csv_with_header_content.splitlines()[skip_lines:])
    assert result.output.strip() == expected.strip()


def test_skip_all_input(runner, csv_with_header_content):
    result = runner.invoke(pyin.cli.main, [
        '--skip', 100,
        'line'
    ], input=csv_with_header_content)
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


def test_multi_infile(path_csv_with_header, runner):
    result = runner.invoke(pyin.cli.main, [
        '-i', path_csv_with_header,
        '-i', path_csv_with_header,
        'line'
    ])
    assert result.exit_code == 0

    expected = ''
    for _ in range(2):
        with open(path_csv_with_header) as f:
            expected += f.read()

    assert result.output == expected


def test_catch_IOError(path_csv_with_header):

    """Python produces an IOError if the input is stdin, and the output is
    stdout piped to another process that does not completely consume the input.
    """

    result = subprocess.check_output(
        "cat {} | pyin line | head -1".format(path_csv_with_header), shell=True)
    assert result.decode().strip() == '"field1","field2","field3"'.strip()
