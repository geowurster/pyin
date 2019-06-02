"""Tests for :module:`pyin.operations`.  Mostly tested indirectly via the
CLI, so these serve as integration tests as well.
"""


import os

import pyin.cli


def test_json(runner):
    result = runner.invoke(
        pyin.cli.main,
        ['%json', 'line + [2]', '%json'],
        input="[0, 1]")
    assert result.exit_code == 0
    assert result.output == "[0, 1, 2]" + os.linesep
