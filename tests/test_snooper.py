#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_snooper
----------------------------------

Tests for `snooper` module.
"""


import sys
import unittest
from contextlib import contextmanager
from click.testing import CliRunner

from snooper import snooper



class TestSnooper(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_000_something(self):
        pass

    def test_command_line_interface(self):
        runner = CliRunner()
        help_result = runner.invoke(snooper.main, ['--help'])
        assert help_result.exit_code == 0
        assert 'Show this message and exit.' in help_result.output

if __name__ == '__main__':
    sys.exit(unittest.main())
