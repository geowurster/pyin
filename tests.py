"""
Unittests for pyin
"""


from __future__ import unicode_literals

import csv
import json
import os
import tempfile
import unittest
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

from click.testing import CliRunner

import pyin


TEST_CONTENT = '''"field1","field2","field3"
"l1f1","l1f2","l1f3"
"l2f1","l2f2","l3f3"
"l3f1","l3f2","l3f3"
"l4f1","l4f2","l4f3"
"l5f1","l5f2","l5f3"'''.strip()


class TestPyin(unittest.TestCase):

    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(mode='r+')
        self.tempfile.write(TEST_CONTENT)
        self.tempfile.seek(0)

    def tearDown(self):
        self.tempfile.close()

    def test_pass_through(self):
        for expected, actual in zip(TEST_CONTENT.splitlines(), pyin.pyin(self.tempfile, 'line')):
            self.assertEqual(expected, actual)

    def test_replace_quotes(self):
        expected_lines = [line.replace('"', "'") for line in TEST_CONTENT.splitlines()]
        for expected, actual in zip(expected_lines, pyin.pyin(self.tempfile, """line.replace('"', "'")""")):
            expected = expected.replace('"', "'")
            self.assertEqual(expected, actual)

    def test_replace_all_lines(self):
        expected = 'wooo'
        for actual in pyin.pyin(self.tempfile, "'%s'" % expected):
            self.assertEqual(expected.strip(), actual.strip())

    def test_yield_true(self):
        expected_lines = [line for line in TEST_CONTENT.splitlines() if 'l2' in line]
        for expected, actual in zip(expected_lines, pyin.pyin(self.tempfile, "'l2' in line", write_true=True)):
            self.assertEqual(expected, actual)


class TestCli(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.tempfile = tempfile.NamedTemporaryFile(mode='r+')
        self.tempfile.write(TEST_CONTENT)
        self.tempfile.seek(0)

    def tearDown(self):
        self.tempfile.close()
    
    def test_pass_through(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "line"])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(TEST_CONTENT.strip(), result.output.strip())

    def test_exception(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, 'raise ValueError("whatever")'])
        self.assertNotEqual(0, result.exit_code)

    def test_change_newline(self):
        nl = '__NL__'
        result = self.runner.invoke(pyin.main,
                                    ['-i', self.tempfile.name, "line", '-nl', nl])
        self.assertEqual(0, result.exit_code)
        expected = nl.join(line for line in TEST_CONTENT.splitlines())
        actual = result.output[:len(result.output) - len(nl)]
        self.assertEqual(expected, actual)

    def test_replace_all_lines(self):
        replace = 'replacement text'
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "'%s'" % replace])
        expected = os.linesep.join([replace for line in TEST_CONTENT.splitlines()])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(expected.strip(), result.output.strip())

    def test_write_true(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "'l2' in line", '-t'])
        expected = os.linesep.join(line for line in TEST_CONTENT.splitlines() if 'l2' in line)
        self.assertEqual(expected.strip(), result.output.strip())

    def test_write_on_true(self):
        expected = 'expected'
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, '"field" in line', '-ot', "'%s'" % expected])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(expected, result.output.strip())

    def test_import_additional_modules(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "str(os.path.isdir(line))", '-im', 'os'])
        expected = os.linesep.join(str(os.path.isdir(line)) for line in TEST_CONTENT.splitlines())
        self.assertEqual(expected.strip(), result.output.strip())

    def test_reader_writer(self):
        result = self.runner.invoke(pyin.main, [
            '-im', 'csv', '-i', self.tempfile.name,
            '-r', 'csv.DictReader', '-w', 'csv.DictWriter', '-wm', 'writerow',
            '-ro', 'fieldnames=["field1","field2"]',
            '-wo', 'fieldnames=["field1","field2"]', '-wo', 'extrasaction=ignore',
            "line"
        ])
        expected = os.linesep.join(["field1,field2", "l1f1,l1f2", "l2f1,l2f2", "l3f1,l3f2", "l4f1,l4f2", "l5f1,l5f2"])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(expected.strip(), result.output.strip())


class TestKeyValToDict(unittest.TestCase):

    def test_standard(self):
        value = ('key1=val1', 'key2=val2', 'key3=val3')
        expected = {'key1': 'val1', 'key2': 'val2', 'key3': 'val3'}
        self.assertDictEqual(expected, pyin._key_val_to_dict(None, None, value))

    def test_exception(self):
        self.assertRaises(ValueError, pyin._key_val_to_dict, None, None, ['nothing'])


def test_default_reader_writer():
    assert hasattr(pyin, 'DefaultReader')
    assert hasattr(pyin, 'DefaultWriter')
