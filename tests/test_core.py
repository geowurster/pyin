"""
Unittests for: pyin.core
"""


import pyin.core


def test_single_expr():

    result = list(pyin.core.pmap("20 <= line <= 80", range(100)))
    assert len(result) == len(list(range(20, 81)))
    for item in result:
        assert 20 <= item <= 80
