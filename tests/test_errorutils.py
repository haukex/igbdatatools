#!/usr/bin/env python3
"""Tests for errorutils library.

Author, Copyright, and License
------------------------------
Copyright (c) 2022 Hauke Daempfling (haukex@zero-g.net)
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, https://www.igb-berlin.de/

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see https://www.gnu.org/licenses/
"""
import unittest
import io
import sys
import subprocess
import inspect
from contextlib import redirect_stderr
from pathlib import Path
from warnings import warn
import errorutils
import tests.errorutils_test_funcs
import tests.errorutils_test_unraisable

class TestErrorUtils(unittest.TestCase):

    def setUp(self):
        self.mybasepath = Path(__file__).parent.parent.joinpath('tests').resolve(strict=True).relative_to(errorutils._basepath)
        self.maxDiff = None

    def test_running_in_unittest(self):
        self.assertTrue(errorutils.running_in_unittest())
        sp = subprocess.run([sys.executable, '-c', 'import errorutils; print(repr(errorutils.running_in_unittest()))'],
            check=True, capture_output=True, cwd=Path(__file__).parent.parent)
        self.assertEqual(b'False', sp.stdout.strip())
        self.assertEqual(b'', sp.stderr)

    def test_excepthook(self):
        sp = subprocess.run([sys.executable, tests.errorutils_test_funcs.__file__],
            capture_output=True, cwd=Path(__file__).parent.parent)
        self.assertNotEqual(0, sp.returncode)
        self.assertEqual(b'', sp.stderr)
        self.assertEqual(
            "TestError('test error 1')\n"
            f"\tat errorutils_test_funcs.py:23 in testfunc3\n"
            f"\tat errorutils_test_funcs.py:18 in testfunc2\n"
            "which caused: ValueError('test error 2')\n"
            f"\tat errorutils_test_funcs.py:20 in testfunc2\n"
            f"\tat errorutils_test_funcs.py:12 in testfunc1\n"
            "which caused: TypeError('test error 3')\n"
            f"\tat errorutils_test_funcs.py:14 in testfunc1\n"
            f"\tat errorutils_test_funcs.py:8 in testfunc0\n"
            f"\tat errorutils_test_funcs.py:29 in <module>\n",
            sp.stdout.decode("ASCII").replace("\r\n","\n") )

    def test_unraisablehook(self):
        sp = subprocess.run([sys.executable, tests.errorutils_test_unraisable.__file__],
            capture_output=True, cwd=Path(__file__).parent.parent)
        self.assertEqual(0, sp.returncode)
        self.assertEqual(b'', sp.stderr)
        self.assertRegex(sp.stdout.decode("ASCII"),
            r'''\AException ignored in: <function Foo\.__del__ at 0x[0-9A-Fa-f]+>\r?\n'''
            r'''RuntimeError\('Bar'\)\r?\n'''
            r'''\tat errorutils_test_unraisable.py:6 in testfunc\r?\n'''
            r'''\tat errorutils_test_unraisable.py:10 in __del__\r?\n\Z''')

    def test_javaishstacktrace(self):
        exline = None
        try:
            exline = inspect.stack()[0].lineno + 1
            tests.errorutils_test_funcs.testfunc0()
        except TypeError as ex:
            self.assertEqual(
                ("tests.errorutils_test_funcs.TestError('test error 1')",
                f"\tat {self.mybasepath/'errorutils_test_funcs.py'}:23 in testfunc3",
                f"\tat {self.mybasepath/'errorutils_test_funcs.py'}:18 in testfunc2",
                "which caused: ValueError('test error 2')",
                f"\tat {self.mybasepath/'errorutils_test_funcs.py'}:20 in testfunc2",
                f"\tat {self.mybasepath/'errorutils_test_funcs.py'}:12 in testfunc1",
                "which caused: TypeError('test error 3')",
                f"\tat {self.mybasepath/'errorutils_test_funcs.py'}:14 in testfunc1",
                f"\tat {self.mybasepath/'errorutils_test_funcs.py'}:8 in testfunc0",
                f"\tat {self.mybasepath/'test_errorutils.py'}:{exline} in test_javaishstacktrace"),
                tuple(errorutils.javaishstacktrace(ex)) )

    def test_customwarn(self):
        with redirect_stderr(io.StringIO()) as s:
            warnline = inspect.stack()[0].lineno
            warn("Test 1")
            with errorutils.CustomHandlers(): warn("Test 2"); \
                warn("Test 3", RuntimeWarning)
            warn("Test 4")
            errorutils.init_handlers(); warn("Test 5")
        self.assertEqual(
            f'{__file__}:{warnline+1}: UserWarning: Test 1\n  warn("Test 1")\n'
            f'UserWarning: Test 2 at {self.mybasepath/"test_errorutils.py"}:{warnline+2}\n'
            f'{__file__}:{warnline+3}: RuntimeWarning: Test 3\n  warn("Test 3", RuntimeWarning)\n'
            f'{__file__}:{warnline+4}: UserWarning: Test 4\n  warn("Test 4")\n'
            f'UserWarning: Test 5 at {self.mybasepath/"test_errorutils.py"}:{warnline+5}\n', s.getvalue())

if __name__ == '__main__':  # pragma: no cover
    unittest.main()