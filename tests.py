"""
Unittests for pyin
"""


import os
import tempfile
import unittest

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

    def test_write_true(self):
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
                                    ['-i', self.tempfile.name, "line", '-l', nl])
        self.assertEqual(0, result.exit_code)
        expected = nl.join(line for line in TEST_CONTENT.splitlines())
        actual = result.output[:len(result.output) - len(nl)]
        self.assertEqual(expected, actual)

    def test_block(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "'nothing'", '--block'])
        self.assertEqual(0, result.exit_code)
        self.assertEqual('nothing', result.output.strip())

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

    def test_import_additional_modules(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "os.path.isdir(line)", '-m', 'os'])
        expected = os.linesep.join(str(os.path.isdir(line)) for line in TEST_CONTENT.splitlines())
        self.assertEqual(expected.strip(), result.output.strip())