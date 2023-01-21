#!/usr/bin/env python3
"""Tests for uniutils.

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
from pathlib import PurePath, Path, PurePosixPath
from tempfile import TemporaryDirectory
import shutil
from copy import deepcopy
from safe_filenames_check import list_problems

expect :tuple[ tuple[ tuple[PurePath, ...], str ], ... ] = (
    ((Path('examples.tgz'), PurePosixPath('Com1.tar.gz')), "filename not allowed in Windows: 'Com1.tar.gz'"),
    ((Path('examples.tgz'), PurePosixPath('lpt3')), "filename not allowed in Windows: 'lpt3'"),
    ((Path('examples.tgz'), PurePosixPath('NUL.TXT')), "filename not allowed in Windows: 'NUL.TXT'"),
    ((Path('examples.tgz'), PurePosixPath('Hello?.txt')), "filename not allowed in Windows: 'Hello?.txt'"),
    ((Path('examples.tgz'), PurePosixPath('Hello.txt ')), "filename not allowed in Windows: 'Hello.txt '"),
    ((Path('examples.tgz'), PurePosixPath('Hello.txt.')), "filename not allowed in Windows: 'Hello.txt.'"),
    ((Path('examples.tgz'), PurePosixPath('Hello\nWorld.txt')), "filename not allowed in Windows: 'Hello\\nWorld.txt'"),
    ((Path('examples.tgz'), PurePosixPath('Hello\r\nWorld.txt')), "filename not allowed in Windows: 'Hello\\r\\nWorld.txt'"),
    ((Path('examples.tgz'), PurePosixPath('Hello.TXT')), f"case collision in ({Path('examples.tgz')!r},): ['HELLO.TXT', 'hello.txt']"),
    ((Path('examples.tgz'), PurePosixPath('Héllö.txt')), "non-ASCII characters ('é',"" 'ö'"")"),
    ((Path('examples.tgz'), PurePosixPath('bar.txt')), 'FileType.SYMLINK'),
    ((Path('examples.tgz'), PurePosixPath('foo.fifo')), 'FileType.OTHER'),
)

class TestSafeFilenamesCheck(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.tempdir = TemporaryDirectory()
        self.testdir = Path(self.tempdir.name)/'bad_win_files'
        self.prevdir = os.getcwd()
        shutil.copytree( Path(__file__).parent.resolve()/'bad_win_files', self.testdir, symlinks=True )
        os.chdir( self.testdir )
        self.expect_all = sorted( deepcopy( expect ) )
        self.extras = []
        try:
            (self.testdir/'foo.tgz').symlink_to('examples.tgz')
            self.extras.append( ( (Path('foo.tgz'),), "symlink") )
        except OSError as ex:  # pragma: no cover
            print(f"Skipping symlink test ({ex})", file=sys.stderr)
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.testdir/'bar.fifo')
            self.extras.append( ( (Path('bar.fifo'),), "FIFO (named pipe)" ) )
        else:  # pragma: no cover
            print("Skipping fifo test (no mkfifo)", file=sys.stderr)
        self.extras.sort()

    def tearDown(self):
        os.chdir( self.prevdir )
        self.tempdir.cleanup()

    def test_list_problems(self):
        everything = self.expect_all + self.extras
        everything.sort()
        self.assertEqual( everything, sorted( list_problems(os.curdir) ) )
        symlinkignored = [ x for x in everything if x[1] not in ("symlink", "FileType.SYMLINK") ]
        self.assertEqual( symlinkignored, sorted( list_problems(os.curdir, ignore_symlinks=True) ) )
        archiveignored = self.extras
        self.assertEqual( archiveignored, sorted( list_problems(os.curdir, ignore_compressed=True) ) )
        withallow = [ (x,y.replace(" 'ö'","")) for x,y in everything ]
        self.assertEqual( withallow, sorted( list_problems(os.curdir, allowed_chars=set("äüöÄÜÖ")) ) )


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
