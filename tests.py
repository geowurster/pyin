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
        actual = "".join(line for line in pyin.pyin(self.tempfile, 'line'))
        self.assertEqual(TEST_CONTENT, actual)

    def test_replace_quotes(self):
        actual = "".join(line for line in pyin.pyin(self.tempfile, """line.replace('"', "'")"""))
        expected = TEST_CONTENT.replace('"', "'")
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
        self.assertEqual(TEST_CONTENT, result.output)

    def test_exception(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, 'raise ValueError("whatever")'])
        self.assertNotEqual(0, result.exit_code)

    def test_change_newline(self):
        nl = '__NL__'
        result = self.runner.invoke(pyin.main,
                                    ['-i', self.tempfile.name, "line.replace(os.linesep, '%s')" % nl, '-im', 'os'])
        self.assertEqual(0, result.exit_code)
        expected = TEST_CONTENT.replace(os.linesep, nl)
        self.assertEqual(expected.strip(), result.output.strip())

    def test_block(self):
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "'nothing'", '--block'])
        self.assertEqual(0, result.exit_code)
        self.assertEqual('nothing', result.output.strip())
