"""Tests for :func:`pyin.compile`."""


import os

import pytest

import pyin


def test_update_scope():

    """:func:`compile` can update an existing scope."""

    scope = {}
    res = pyin.importer('os.path.exists(line)', scope=scope)

    assert res is scope
    assert scope == {'os': os}
