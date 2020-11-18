# -*- coding: utf-8 -*-


"""
Unittests for $ pyin
"""


import json
import os
import sys
import subprocess
import textwrap

import pytest


def test_single_expr(runner, csv_with_header_content):
    result = runner.invoke([
        "line.upper()"
    ], input=csv_with_header_content)
    assert result.exit_code == 0
    assert result.output.strip() == csv_with_header_content.upper().strip()


def test_multiple_expr(runner, path_csv_with_header):
    expected = os.linesep.join((
        "0FIELD10,0FIELD20,0FIELD30",
        "0l1f10,0l1f20,0l1f30",
        "0l2f10,0l2f20,0l2f30",
        "0l3f10,0l3f20,0l3f30",
        "0l4f10,0l4f20,0l4f30",
        "0l5f10,0l5f20,0l5f30"))
    result = runner.invoke([
        '-i', path_csv_with_header,
        "line.upper() if 'field' in line else line",
        "line.replace('\"', '0')"
    ])
    assert result.exit_code == 0
    assert result.output.strip() == expected.strip()


def test_with_generator(runner, csv_with_header_content):
    result = runner.invoke([
        "(i for i in line)"
    ], input=csv_with_header_content)
    assert result.exit_code == 0
    assert os.linesep.join(
        [json.dumps(list((i for i in line))) for line in csv_with_header_content.splitlines()])


def test_with_blank_lines(runner):
    result = runner.invoke([
        'line'
    ], input="")
    assert result.exit_code == 0
    assert result.output == ''


def test_block_mode(runner):
    text = json.dumps({k: None for k in range(10)}, indent=4)
    assert len(text.splitlines()) > 1

    result = runner.invoke([
        "--block",
        "json.loads(line)",
        "{k: v for k, v in line.items() if int(k) in range(5)}",
        "json.dumps(line)"
    ], input=text)
    assert result.exit_code == 0

    expected = '{"3": null, "4": null, "0": null, "2": null, "1": null}'
    assert json.loads(expected) == json.loads(result.output)


@pytest.mark.skipif(sys.version_info.major == 2, reason="Unicode. Ugh.")
def test_unicode(runner):

    text = u"""Héllö"""
    result = runner.invoke([
        'line.upper()'
    ], input=text)
    assert result.exit_code == 0
    assert result.output.strip() == text.strip().upper()


@pytest.mark.parametrize("skip_lines", [1, 3])
def test_skip_single_line(runner, skip_lines, csv_with_header_content):
    result = runner.invoke([
        '--skip', str(skip_lines),
        'line'
    ], input=csv_with_header_content)
    assert result.exit_code == 0
    expected = os.linesep.join(csv_with_header_content.splitlines()[skip_lines:])
    assert result.output.strip() == expected.strip()


def test_skip_all_input(runner, csv_with_header_content):
    result = runner.invoke([
        '--skip', '100',
        'line'
    ], input=csv_with_header_content)
    assert result.exit_code == 0
    assert result.output == ''


def test_repr(runner):

    text = """
    2015-01-01
    2015-01-02
    2015-01-03
    """.strip()

    result = runner.invoke([
        "line.strip()",
        "datetime.datetime.strptime(line, '%Y-%m-%d')",
        "%filter", "isinstance(line, datetime.datetime)"
    ], input=text)

    assert result.exit_code == 0
    assert result.output.strip() == textwrap.dedent("""
    datetime.datetime(2015, 1, 1, 0, 0)
    datetime.datetime(2015, 1, 2, 0, 0)
    datetime.datetime(2015, 1, 3, 0, 0)
    """).strip()


def test_catch_IOError(path_csv_with_header):

    """Python produces an IOError if the input is stdin, and the output is
    stdout piped to another process that does not completely consume the input.
    """

    result = subprocess.check_output(
        "cat {} | pyin line | head -1".format(path_csv_with_header), shell=True)
    assert result.decode().strip() == '"field1","field2","field3"'.strip()
