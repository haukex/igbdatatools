#!/usr/bin/env python3
"""Tests for fileutils library.

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
import sys
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from fileutils import to_Paths, autoglob, Pushd, filetypestr, is_windows_filename_bad, replacer

class TestFileUtils(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_to_paths(self):
        s = __file__
        b = os.fsencode(__file__)
        p = Path(__file__)
        self.assertEqual( (p,), tuple(to_Paths(s)) )
        self.assertEqual( (p,), tuple(to_Paths(b)) )
        self.assertEqual( (p,), tuple(to_Paths(p)) )
        self.assertEqual( (p,p,p), tuple(to_Paths((s,b,p))) )
        with self.assertRaises(TypeError):
            tuple( to_Paths((123,)) )

    def test_autoglob(self):
        testpath = Path(__file__).parent
        testglob = str(testpath/'*utils*.py')
        noglob = str(testpath/'zdoesntexist*')
        files = sorted( str(p) for p in testpath.iterdir() if 'utils' in p.name and p.name.endswith('.py') )
        self.assertTrue(len(files)>3)
        # this doesn't really test expanduser but that's ok
        self.assertEqual( files+[noglob], sorted(autoglob([testglob, noglob], force=True)) )
        self.assertEqual( files if sys.platform.startswith('win32') else [testglob], list(autoglob([testglob])) )

    def test_pushd(self):
        prevwd = os.getcwd()
        with (TemporaryDirectory() as td1, TemporaryDirectory() as td2):
            # basic pushd
            with Pushd(td1):
                self.assertEqual(os.getcwd(), td1)
                with Pushd(td2):
                    self.assertEqual(os.getcwd(), td2)
                self.assertEqual(os.getcwd(), td1)
            self.assertEqual(os.getcwd(), prevwd)
            # exception inside the `with`
            class BogusError(RuntimeError): pass
            with self.assertRaises(BogusError):
                with Pushd(td2):
                    self.assertEqual(os.getcwd(), td2)
                    raise BogusError()
            self.assertEqual(os.getcwd(), prevwd)
            # attempting to change into a nonexistent directory
            with self.assertRaises(FileNotFoundError):
                with Pushd('thisdirectorydoesnotexist'):  # the exception happens here
                    self.fail()  # pragma: no cover
            # attempting to change back to a directory that no longer exists
            with TemporaryDirectory() as td3:
                with self.assertRaises(FileNotFoundError):
                    with Pushd(td3):
                        with Pushd(td2):
                            os.rmdir(td3)
                    # the exception happens here
                    self.fail()  # pragma: no cover

    def test_filetypestr(self):
        with TemporaryDirectory() as td:
            tp = Path(td)
            with open(tp/'foo', 'w') as fh: print("foo", file=fh)
            (tp/'bar').mkdir()
            self.assertEqual( 'regular file', filetypestr( os.lstat(tp/'foo') ) )
            self.assertEqual( 'directory', filetypestr( os.lstat(tp/'bar') ) )
            try:
                (tp/'baz').symlink_to('foo')
            except OSError as ex:  # pragma: no cover
                print(f"Skipping symlink test ({ex})", file=sys.stderr)
            else:
                self.assertEqual( 'symbolic link', filetypestr( os.lstat(tp/'baz') ) )
            if hasattr(os, 'mkfifo'):
                os.mkfifo(tp/'quz')
                self.assertEqual( 'FIFO (named pipe)', filetypestr( os.lstat(tp/'quz') ) )
            else:  # pragma: no cover
                print("Skipping fifo test (no mkfifo)", file=sys.stderr)

    def test_is_windows_filename_bad(self):
        self.assertFalse( is_windows_filename_bad("Hello.txt") )
        self.assertFalse( is_windows_filename_bad("Hello .txt") )
        self.assertFalse( is_windows_filename_bad(".Hello.txt") )
        self.assertFalse( is_windows_filename_bad("Héllö.txt") )
        self.assertTrue( is_windows_filename_bad("Hello?.txt") )
        self.assertTrue( is_windows_filename_bad("Hello\tWorld.txt") )
        self.assertTrue( is_windows_filename_bad("Hello\0World.txt") )
        self.assertTrue( is_windows_filename_bad("lpt3") )
        self.assertTrue( is_windows_filename_bad("NUL.txt") )
        self.assertTrue( is_windows_filename_bad("Com1.tar.gz") )
        self.assertTrue( is_windows_filename_bad("Hello.txt ") )
        self.assertTrue( is_windows_filename_bad("Hello.txt.") )

    def test_replacer(self):
        try:
            # Basic Test
            with NamedTemporaryFile('w', delete=False) as tf:
                print("Hello\nWorld!", file=tf)
            with replacer(tf.name) as (ifh, ofh):
                for line in ifh:
                    line = line.replace('o', 'u')
                    print(line, end='', file=ofh)
            self.assertFalse( os.path.exists(ofh.name) )
            with open(tf.name) as fh:
                self.assertEqual(fh.read(), "Hellu\nWurld!\n")

            # Binary
            with open(tf.name, 'wb') as fh:
                fh.write(b"Hello, World")
            with replacer(tf.name, binary=True) as (ifh, ofh):
                data = ifh.read()
                data = data.replace(b"o", b"u")
                ofh.write(data)
            self.assertFalse( os.path.exists(ofh.name) )
            with open(tf.name, 'rb') as fh:
                self.assertEqual(fh.read(), b"Hellu, Wurld")

            # Already open handle
            if sys.platform.startswith('win32'):
                print(f"Skipping test with open file", file=sys.stderr)
                expect = "Hellu, Wurld"
            else:
                expect = "Heiiu, Wurid"
                with open(tf.name) as ifh:
                    with replacer(ifh) as (_, ofh):
                        data = ifh.read()
                        data = data.replace("l","i")
                        ofh.write(data)
            self.assertFalse( os.path.exists(ofh.name) )
            with open(tf.name) as fh:
                self.assertEqual(fh.read(), expect)

            # Failure inside of context
            with self.assertRaises(ProcessLookupError):
                with replacer(tf.name) as (ifh, ofh):
                    ofh.write("oops")
                    raise ProcessLookupError("blam!")
            self.assertFalse( os.path.exists(ofh.name) )
            with open(tf.name) as fh:
                self.assertEqual(fh.read(), expect)

        finally:
            os.unlink(tf.name)

        # Test errors
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            with replacer(bytes()): pass
        with self.assertRaises(ValueError):
            with replacer(Path(tf.name).parent): pass

        # Permissions test
        if not sys.platform.startswith('win32'):
            try:
                with NamedTemporaryFile('w', delete=False) as tf:
                    print("Hello\nWorld!", file=tf)
                orig_ino = os.stat(tf.name).st_ino
                os.chmod(tf.name, 0o741)
                with replacer(tf.name): pass
                st = os.stat(tf.name)
                self.assertNotEqual( st.st_ino, orig_ino )
                self.assertEqual( stat.S_IMODE(st.st_mode), 0o741 )
            finally:
                os.unlink(tf.name)
        else:
            print(f"Skipping chmod test", file=sys.stderr)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
