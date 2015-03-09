"""
Unittests for pyin
"""


from __future__ import unicode_literals

import datetime
import os
import tempfile
import unittest
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

from click.testing import CliRunner

import pyin


os.environ[pyin._NO_WARN_ENV_KEY] = pyin._NO_WARN_ENV_VAL


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
        # Pass the line through unaltered
        actual = ''.join([line for line in pyin.pyin('line', self.tempfile)])
        self.assertEqual(TEST_CONTENT, actual)

    def test_replace_quotes(self):
        # Replace ' with "
        expected_lines = [line.replace('"', "'") for line in TEST_CONTENT.splitlines()]
        for expected, actual in zip(expected_lines, pyin.pyin("""line.replace('"', "'")""", self.tempfile)):
            expected = expected.replace('"', "'")
            self.assertEqual(expected.strip(), actual.strip())

    def test_replace_all_lines(self):
        # Replace all lines with the same string
        expected = 'wooo'
        for actual in pyin.pyin("'%s'" % expected, self.tempfile):
            self.assertEqual(expected, actual)

    def test_yield_true(self):
        # Perform a True/False evaluation on all lines
        expected_lines = [line for line in TEST_CONTENT.splitlines() if 'l2' in line]
        for expected, actual in zip(expected_lines, pyin.pyin("'l2' in line", self.tempfile, write_true=True)):
            self.assertEqual(expected + os.linesep, actual)

    def test_line_in_scope_raise_exception(self):
        # When line is provided in the scope it will be immediately overwritten by the local variable line
        # so prevent this from happening by raising an exception
        with self.assertRaises(NameError):
            for item in pyin.pyin("'line'", range(10), scope={'line': 'asdf'}):
                pass

    def test_reach_outside_scope_raise_exception(self):
        # An exception will be raised if the user attempts to access something that is not in the scope
        with self.assertRaises(NameError):
            for item in pyin.pyin("os", range(5)):
                pass


class TestCli(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.tempfile = tempfile.NamedTemporaryFile(mode='r+')
        self.tempfile.write(TEST_CONTENT)
        self.tempfile.seek(0)

    def tearDown(self):
        self.tempfile.close()

    def test_pass_through(self):
        # Pass all lines through unaltered
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "line"])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(TEST_CONTENT, result.output)

    def test_exception(self):
        # Explicitly raise an exception in the expression
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, 'raise ValueError("whatever")'])
        self.assertNotEqual(0, result.exit_code)

    def test_change_linesep(self):
        # Change newline character from os.linesep to something else
        nl = '__NL__'
        result = self.runner.invoke(pyin.main,
                                    ['-im', 'os', '-i', self.tempfile.name, """line.replace(os.linesep, "%s")""" % nl])
        self.assertEqual(0, result.exit_code)
        expected = nl.join(line for line in TEST_CONTENT.splitlines())
        self.assertEqual(expected, result.output)

    def test_replace_all_lines(self):
        # Replace all lines with the same text
        replace = 'replacement text'
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "'%s'" % replace])
        expected = ''.join([replace for line in TEST_CONTENT.splitlines()])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(expected, result.output)

    def test_write_true(self):
        # Only write lines whose expression evaluates as True
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "'l2' in line", '-t'])
        expected = os.linesep.join(line for line in TEST_CONTENT.splitlines() if 'l2' in line)
        self.assertEqual(expected.strip(), result.output.strip())

    def test_write_on_true(self):
        # For every line whose expression evaluates as True, make the line some specific text
        expected = 'expected'
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, '"field" in line', '-ot', "'%s'" % expected])
        self.assertEqual(0, result.exit_code)
        self.assertEqual(expected, result.output)

    def test_import_additional_modules(self):
        # Import an additional module and use it in the expression - all should evaluate as False
        # All results should be written to the same line because the linesep character has not been added to the end
        # of the line
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "str(os.path.isdir(line))", '-im', 'os'])
        expected = ''.join(str(os.path.isdir(line)) for line in TEST_CONTENT.splitlines())
        self.assertEqual(expected, result.output)

    def test_reader_writer(self):
        # Read with a specific reader and write with a specific writer
        result = self.runner.invoke(pyin.main, [
            '-im', 'csv', '-i', self.tempfile.name,
            '-r', 'csv.DictReader', '-w', 'csv.DictWriter', '-wm', 'writerow',
            '-ro', 'fieldnames=["field1","field2"]',
            '-wo', 'fieldnames=["field1","field2"]', '-wo', 'extrasaction=ignore',
            "line"
        ])
        expected = os.linesep.join(["field1,field2", "l1f1,l1f2", "l2f1,l2f2", "l3f1,l3f2", "l4f1,l4f2", "l5f1,l5f2"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(expected + os.linesep, result.output)

    def test_block(self):
        # Evaluate expression against all lines as a single block of text
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "'nothing'", '--block'])
        self.assertEqual(0, result.exit_code)
        self.assertEqual('nothing', result.output)

    def test_variable(self):
        # Add a new variable to the scope and make every output line that string
        new_var = 'WOO'
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "new_var", '-v', 'new_var=%s' % new_var])
        self.assertEqual(0, result.exit_code)
        expected = ''.join(new_var for line in self.tempfile)
        self.assertEqual(expected, result.output)

    def test_statement(self):
        # Execute a statement immediately after importing additional modules
        # In this case an additional line is printed to stdout, which is captured and used in the test comparison
        print_line = 'WOO'
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "line", '-s', "print('%s')" % print_line])
        self.assertEqual(0, result.exit_code)
        expected = print_line + os.linesep + TEST_CONTENT
        self.assertEqual(expected.strip(), result.output.strip())

    def test_lines(self):
        # Only process 2 lines
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile.name, "line", '-l', '2'])
        self.assertEqual(0, result.exit_code)
        expected = os.linesep.join(TEST_CONTENT.splitlines()[:2])
        self.assertEqual(expected.strip(), result.output.strip())

    def test_lines_bad_value(self):
        # Make sure an exception is raised when supplying a bad number of lines
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile, "line", '-l', '-1'])
        self.assertNotEqual(0, result.exit_code)
        self.assertTrue(result.output.startswith('ERROR'))
        self.assertTrue('int' in result.output and 'positive' in result.output)

    def test_import_module_as(self):
        # The syntax `import something as other` is not directly supported but can be achieved with
        # `-im other=something`
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile, "_os.isdir", '-im', '_os=os.path'])
        expected = str(os.path.isdir) * len([line for line in TEST_CONTENT.splitlines()])
        self.assertEqual(expected, result.output)

    def test_skip_lines(self):
        # Allow user to skip some number of input lines
        skip_lines = 2
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile, "line", '-sl', str(skip_lines)])
        expected = os.linesep.join([line for line in TEST_CONTENT.splitlines()][skip_lines:])
        self.assertEqual(expected, result.output)

    def test_only_process_subset(self):
        # Allow the user to process the first N lines
        subset = 2
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile, "line", '-l', str(subset)])
        expected = os.linesep.join([line for line in TEST_CONTENT.splitlines()][:subset]) + os.linesep
        self.assertEqual(expected, result.output)

    def test_skip_lines_and_process_subset(self):
        # Allow the user to both skip N input lines and then only process the next N lines
        skip_lines = 2
        subset = 2
        result = self.runner.invoke(
            pyin.main, ['-i', self.tempfile, "line", '-sl', str(skip_lines), '-l', str(subset)])
        expected = os.linesep.join(
            [line for line in TEST_CONTENT.splitlines()][skip_lines:skip_lines + subset]
        ) + os.linesep
        self.assertEqual(expected, result.output)

    def test_invalid_skip_lines(self):
        # Make sure an error is thrown if the user specifies an invalid number of skip lines
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile, "line", "-sl", "-1"])
        self.assertNotEqual(0, result.exit_code)
        self.assertTrue(result.output.startswith('ERROR:'))
        self.assertTrue('int' in result.output and 'positive' in result.output)

    def test_rules_flag(self):
        # Make sure this flag only prints the rules and exits
        result = self.runner.invoke(pyin.main, ['--rules'])
        self.assertEqual(pyin.RULES.strip(), result.output.strip())

    def test_print_warning(self):
        # Make sure the warning is printed and there's a pause before executing
        if pyin._NO_WARN_ENV_KEY in os.environ:
            del os.environ[pyin._NO_WARN_ENV_KEY]
        pyin._WAIT_TIME = 3
        start_time = datetime.datetime.utcnow()
        result = self.runner.invoke(pyin.main, ['-i', self.tempfile, "line"])
        end_time = datetime.datetime.utcnow()
        self.assertTrue(result.output.startswith(pyin.RULES))
        self.assertTrue((end_time - start_time).total_seconds() - pyin._WAIT_TIME < 0.5)
        os.environ[pyin._NO_WARN_ENV_KEY] = pyin._NO_WARN_ENV_VAL


class TestDefaultReader(unittest.TestCase):

    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(mode='r+')
        self.tempfile.write(TEST_CONTENT)
        self.tempfile.seek(0)

    def tearDown(self):
        self.tempfile.close()

    def test_iter(self):
        for expected, actual in zip(pyin._DefaultReader(self.tempfile), StringIO(TEST_CONTENT)):
            self.assertEqual(expected, actual)


class TesetDefaultWriter(unittest.TestCase):

    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(mode='r+')

    def tearDown(self):
        self.tempfile.close()

    def test_write(self):
        writer = pyin._DefaultWriter(self.tempfile)
        for line in TEST_CONTENT.splitlines():
            writer.write(line + os.linesep)
        self.tempfile.seek(0)
        for expected, actual in zip(TEST_CONTENT.splitlines(), self.tempfile):
            self.assertEqual(expected + os.linesep, actual)


def test_parse_scope():
    scope = {'os': os}
    assert pyin._parse_scope(scope, 'os.path.isdir') == os.path.isdir
