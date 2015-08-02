import json
import os
from os import path

from click.testing import CliRunner

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
        'tests.module.function(line)'
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
