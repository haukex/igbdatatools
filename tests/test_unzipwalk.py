#!/usr/bin/env python3
"""Tests for unzipwalk.

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
import os
import sys
from copy import deepcopy
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import shutil
from unzipwalk import unzipwalk, FileType

expect = (
    ( (Path("test.csv"),), b'"ID","Name","Age"\n1,"Foo",23\n2,"Bar",45\n3,"Quz",67\n', FileType.FILE ),
    ( (Path("WinTest.ZIP"),), None, FileType.ARCHIVE ),
    ( (Path("WinTest.ZIP"), PurePosixPath("Foo.txt")),
        b"Foo\r\nBar\r\n", FileType.FILE ),
    # Note the WinTest.ZIP doesn't contain an entry for the "World/" dir
    # (this zip was created with Windows Explorer, everything else on Linux)
    ( (Path("WinTest.ZIP"), PurePosixPath("World/Hello.txt")),
        b"Hello\r\nWorld", FileType.FILE ),
    ( (Path("archive.tar.gz"),), None, FileType.ARCHIVE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/")), None, FileType.DIR ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/abc.zip")), None, FileType.ARCHIVE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/abc.zip"), PurePosixPath("abc.txt")),
        b"One two three\nfour five six\nseven eight nine\n", FileType.FILE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/abc.zip"), PurePosixPath("def.txt")),
        b"3.14159\n", FileType.FILE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/iii.dat")),
        b"jjj\nkkk\nlll\n", FileType.FILE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/world.txt.gz")), None, FileType.ARCHIVE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/world.txt.gz"), PurePosixPath("archive/world.txt")),
        b"This is a file\n", FileType.FILE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/xyz.txt")),
        b"XYZ!\n", FileType.FILE ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/fifo")), None, FileType.OTHER ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/test2/")), None, FileType.DIR ),
    ( (Path("archive.tar.gz"), PurePosixPath("archive/test2/jjj.dat")), None, FileType.SYMLINK ),
    ( (Path("linktest.zip"),), None, FileType.ARCHIVE ),
    ( (Path("linktest.zip"), PurePosixPath("linktest/") ), None, FileType.DIR ),
    ( (Path("linktest.zip"), PurePosixPath("linktest/hello.txt")),
        b"Hi there\n", FileType.FILE ),
    ( (Path("linktest.zip"), PurePosixPath("linktest/world.txt")), None, FileType.SYMLINK ),
    ( (Path("more.zip"),), None, FileType.ARCHIVE ),
    ( (Path("more.zip"), PurePosixPath("more/")), None, FileType.DIR ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/")), None, FileType.DIR ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/five.txt")),
        b"5\n5\n5\n5\n5\n", FileType.FILE ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/six.txt")),
        b"6\n6\n6\n6\n6\n6\n", FileType.FILE ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/four.txt")),
        b"4\n4\n4\n4\n", FileType.FILE ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/texts.tgz")), None, FileType.ARCHIVE ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/texts.tgz"), PurePosixPath("one.txt")),
        b"111\n11\n1\n", FileType.FILE ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/texts.tgz"), PurePosixPath("two.txt")),
        b"2222\n222\n22\n2\n", FileType.FILE ),
    ( (Path("more.zip"), PurePosixPath("more/stuff/texts.tgz"), PurePosixPath("three.txt")),
        b"33333\n3333\n333\n33\n3\n", FileType.FILE ),
    ( (Path("subdir"),), None, FileType.DIR ),
    ( (Path("subdir","ooo.txt"),),
        b"oOoOoOo\n\n", FileType.FILE ),
    ( (Path("subdir","foo.zip"), PurePosixPath("hello.txt")),
        b"Hallo\nWelt\n", FileType.FILE ),
    ( (Path("subdir","foo.zip"),), None, FileType.ARCHIVE ),
    ( (Path("subdir","foo.zip"), PurePosixPath("foo/")), None, FileType.DIR ),
    ( (Path("subdir","foo.zip"), PurePosixPath("foo/bar.txt")),
        b"Blah\nblah\n", FileType.FILE ),
)

class TestUnzipWalk(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.tempdir = TemporaryDirectory()
        self.testdir = Path(self.tempdir.name)/'zips'
        self.prevdir = os.getcwd()
        shutil.copytree( Path(__file__).parent.resolve()/'zips', self.testdir, symlinks=True )
        os.chdir( self.testdir )
        self.expect_all = list( deepcopy( expect ) )
        try:
            (self.testdir/'baz.zip').symlink_to('more.zip')
            self.expect_all.append( ( (Path("baz.zip"),), None, FileType.SYMLINK ) )
        except OSError as ex:  # pragma: no cover
            print(f"Skipping symlink test ({ex})", file=sys.stderr)
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.testdir/'xy.fifo')
            self.expect_all.append( ( (Path("xy.fifo"),), None, FileType.OTHER ) )
        else:  # pragma: no cover
            print("Skipping fifo test (no mkfifo)", file=sys.stderr)
        self.expect_all.sort()

    def tearDown(self):
        os.chdir( self.prevdir )
        self.tempdir.cleanup()

    def test_unzipwalk(self):
        self.assertEqual(
            sorted( x for x in self.expect_all if x[-1]==FileType.FILE ),
            sorted( (fns, fh.read(), ft) for fns, fh, ft in unzipwalk(os.curdir) ) )

    def test_unzipwalk_all(self):
        self.assertEqual(self.expect_all,
            sorted(
                ( fns, fh.read() if ft==FileType.FILE else None, ft)
                for fns, fh, ft in unzipwalk(os.curdir, onlyfiles=False )
            ) )

    def test_unzipwalk_errs(self):
        with self.assertRaises(FileNotFoundError):
            list(unzipwalk('/thisfileshouldnotexist'))

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
