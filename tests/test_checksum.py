#!/usr/bin/env python3
"""Tests for file checksumming tool.

Author, Copyright, and License
------------------------------
Copyright (c) 2023 Hauke Daempfling (haukex@zero-g.net)
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
from pathlib import Path, PurePath
import shutil
from tempfile import TemporaryDirectory
from checksum import check_hashes, match_hashes, ResultCode, list_hashable_files
from hashedfile import HashedFile
import hashlib
from fileutils import Pushd

class TestChecksum(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        # note the prefix is important here, because several tests depend on tmp_*/symlink being sorted before the x/*.txt and y/*.txt entries
        self.tempdirs: list[TemporaryDirectory] = [ TemporaryDirectory(prefix='tmp_'), TemporaryDirectory(prefix='tmp_') ]
        # we need to do a resolve on these because on Windows we need to expand short filenames that might be in self.td1/2
        self.td1 = Path(self.tempdirs[0].name).resolve()
        with open(self.td1/"a.txt", "w", encoding="ASCII") as fh: print("AAAAA", file=fh, end="")
        with open(self.td1/"b.txt", "w", encoding="ASCII") as fh: print("BBBBBB", file=fh, end="")
        with open(self.td1/"c.txt", "w", encoding="ASCII") as fh: print("CCCCCCC", file=fh, end="")
        with open(self.td1/"d.txt", "w", encoding="ASCII") as fh: print("DDDDDDDD", file=fh, end="")
        self.sumfile1 = tuple(map(HashedFile.from_line, (
            "f6a6263167c92de8644ac998b3c4e4d1 *a.txt",
            "25363e98eb50cc813f0d3eff743f34908419b557 *b.txt",
            "d1cf7fb693b553eeca55dc40f1e93af6e89b7fd803c2f7e689aab4ca16257d0a *c.txt",
            "9e79b63d8057ed9491ea95a4afa02588dac66e229abd08e8a44866f15ce9381c25a78aa891238e808f711bcf3c89c3aa6480bba392208a5b8c5fe35db1ac87b7 *d.txt" ) ))
        self.td2 = Path(self.tempdirs[1].name).resolve()
        td2x = self.td2/'x'; td2x.mkdir()
        td2y = self.td2/'y'; td2y.mkdir()
        with open(td2x/"a.txt", "w", encoding="ASCII") as fh: print("AAAAA", file=fh, end="")
        with open(td2x/"b.txt", "w", encoding="ASCII") as fh: print("BBBBBB", file=fh, end="")
        with open(td2y/"c.txt", "w", encoding="ASCII") as fh: print("CCCCCCC", file=fh, end="")
        with open(td2y/"d.txt", "w", encoding="ASCII") as fh: print("DDDDDDDD", file=fh, end="")
        self.sumfile2a = tuple(map(HashedFile.from_line, (
            "f6a6263167c92de8644ac998b3c4e4d1 *x/a.txt",
            "25363e98eb50cc813f0d3eff743f34908419b557 *x/b.txt" ) ))
        self.sumfile2b = tuple(map(HashedFile.from_line, (
            "d1cf7fb693b553eeca55dc40f1e93af6e89b7fd803c2f7e689aab4ca16257d0a *y/c.txt",
            "9e79b63d8057ed9491ea95a4afa02588dac66e229abd08e8a44866f15ce9381c25a78aa891238e808f711bcf3c89c3aa6480bba392208a5b8c5fe35db1ac87b7 *y/d.txt" ) ))
        try:
            (self.td2/'symlink').symlink_to("x/a.txt")
            self.symlink = self.td2/'symlink'
        except OSError:  # pragma: no cover
            # probably Windows
            print("Not including symlink in tests", file=sys.stderr)
            self.symlink = None

    def tearDown(self):
        for td in self.tempdirs: td.cleanup()
        self.tempdirs.clear()

    def test_list_hashable_files(self):
        expect_fns = [ self.td2/'x'/'a.txt', self.td2/'x'/'b.txt', self.td2/'y'/'c.txt', self.td2/'y'/'d.txt' ]
        expect_codes = [ResultCode.NONE] * 4
        expect_msg :list[str|None] = [None]*4
        expect_rel = [str(Path("x","a.txt")), str(Path("x","b.txt")), str(Path("y","c.txt")), str(Path("y","d.txt"))]
        if hasattr(os, 'mkfifo') and self.symlink:  # probably a POSIX system
            os.mkfifo( self.td2/'fifo' )
            expect_fns.extend([self.td2 /'fifo', self.symlink])
            expect_codes.extend([ResultCode.SKIP] * 2)
            expect_msg.append(f"skipping FIFO (named pipe) {self.td2/'fifo'}")
            expect_msg.append(f"skipping symlink {self.symlink} -> x/a.txt")
            expect_rel.extend(["fifo","symlink"])
        else: pass  # pragma: no cover
        rv = sorted( list_hashable_files(self.td2), key=lambda _: _.fn.name )
        self.assertEqual( expect_fns, [ r.fn for r in rv ] )
        self.assertEqual( expect_codes, [ r.code for r in rv ] )
        self.assertEqual( expect_msg, [ r.msg for r in rv ] )
        with Pushd( self.td2 ):
            rv = sorted(list_hashable_files(os.curdir), key=lambda _: _.fn.name)
            self.assertEqual( expect_rel, [ r.origfn for r in rv ] )
        # test an invalid filename passed in:
        with self.assertRaises(FileNotFoundError):
            list( list_hashable_files( self.td2/'foobar') )
        # test the report_dirs option:
        fns_with_dirs = sorted( expect_fns + [ self.td2/'x', self.td2/'y' ], key=lambda _: _.name )
        rv = sorted( list_hashable_files(self.td2, report_dirs=True), key=lambda _: _.fn.name )
        self.assertEqual( fns_with_dirs, [ r.fn for r in rv ] )

    def test_hash_me(self):
        frs = sorted( list_hashable_files(self.td2), key=lambda _: _.fn.name )
        fr1 = frs[-2 if self.symlink else -1].hash_me(algo=hashlib.md5, check_code=False)
        self.assertEqual( fr1.fn.name, 'd.txt' )
        self.assertEqual( fr1.hsh.hsh, bytes.fromhex('22bf7d52880f553b1a82a4fe01dd5d3a') )
        fr2 = fr1.hash_me(algo=hashlib.md5, check_code=False)
        self.assertEqual( fr1, fr2 )
        fr3 = fr2.hash_me(algo=hashlib.sha1, check_code=False)
        self.assertEqual( fr3.hsh.hsh, bytes.fromhex('c28203384fe0260d8bea44acf0474db65fe5898b') )
        if self.symlink: frs[-1].hash_me(check_code=True)  # code coverage for the SKIP case
        frk = fr1._replace( code=ResultCode.SUMOK )
        frk.hash_me(algo=hashlib.md5, check_code=True)
        frx = fr2._replace( code=ResultCode.SUMMISMATCH )
        with self.assertRaises(ValueError):
            frx.hash_me(algo=hashlib.md5, check_code=True)

    def test_gen_hashes(self):
        # note the previous gen_hashes has essentially been replaced by the following generator expression
        gen_hashes = ( fr.hash_me(algo=hashlib.md5).hsh for fr in list_hashable_files(self.td2) if fr.code != ResultCode.SKIP )
        hashes = sorted( gen_hashes, key=lambda _: _.fn.name )
        exp = list(map(HashedFile.from_line, (
            f"f6a6263167c92de8644ac998b3c4e4d1 *{self.td2/'x'/'a.txt'}",
            f"fa0903293ec8fc1f19087d0eb2ffded8 *{self.td2/'x'/'b.txt'}",
            f"c36e60f574001ef3de0a551f950bdb39 *{self.td2/'y'/'c.txt'}",
            f"22bf7d52880f553b1a82a4fe01dd5d3a *{self.td2/'y'/'d.txt'}" ) ))
        self.assertEqual( exp, hashes )

    def test_match_hashes(self):
        with open(self.td1/"a.txt", "w", encoding="ASCII") as fh: print("AAAAa", file=fh, end="")
        (self.td1/'b.txt').rename(self.td1/'e.txt')
        rv = sorted( match_hashes(sumsrc=self.sumfile1, paths=self.td1), key=lambda _: _.fn.name )
        self.assertEqual( ["a.txt","b.txt","c.txt","d.txt","e.txt"], [ r.fn.name for r in rv ] )
        self.assertEqual( [ResultCode.NEEDSVALIDATE, ResultCode.MISSING, ResultCode.NEEDSVALIDATE,
                           ResultCode.NEEDSVALIDATE, ResultCode.NOSUM ], [r.code for r in rv])
        rv2 = list( check_hashes(rv) )
        self.assertEqual( ["a.txt","b.txt","c.txt","d.txt","e.txt"], [ r.fn.name for r in rv2 ] )
        self.assertEqual( [ResultCode.SUMMISMATCH, ResultCode.MISSING, ResultCode.SUMOK,
                           ResultCode.SUMOK, ResultCode.NOSUM ], [r.code for r in rv2])

    # ##### ##### ##### Begin tests of check_hashes(match_hashes(...)) ##### ##### #####

    def test_basic(self):
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1, paths=self.td1)), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertEqual( ["a.txt","b.txt","c.txt","d.txt"], [ r.origfn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )
        self.assertEqual( ["a.txt","b.txt","c.txt","d.txt"], [ PurePath(r.hsh.fn).name for r in rv ] )
        self.assertTrue( all( r.hsh.valid for r in rv ) )
        self.assertEqual( self.sumfile1, tuple( r.hsh.setfn(Path(r.hsh.fn).name) for r in rv ) )
    def test_basic_rel(self):
        with Pushd( self.td1 ):
            rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1, paths=os.curdir)), key=lambda _: _.fn.name )
            self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
            self.assertEqual( ["a.txt","b.txt","c.txt","d.txt"], [ r.origfn for r in rv ] )
            self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )
    def test_basic_abs(self):
        sumfile1_abs = [ h.setfn( self.td1/h.fn ) for h in self.sumfile1 ]
        rv = sorted( check_hashes(match_hashes(sumsrc=sumfile1_abs, paths=self.td1)), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertEqual( [ str(self.td1/f) for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.origfn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )

    def test_file_source_td1(self):
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1, paths=self.td1, filesrc=list_hashable_files(self.td1))), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertEqual( ["a.txt","b.txt","c.txt","d.txt"], [ r.origfn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )
    def test_file_source_td2(self):
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile2a + self.sumfile2b, paths=self.td2,
                                               filesrc=list_hashable_files((self.td2 / 'x', self.td2 / 'y')))), key=lambda _: _.fn.name )
        self.assertEqual( [self.td2/'x'/'a.txt',self.td2/'x'/'b.txt',self.td2/'y'/'c.txt',self.td2/'y'/'d.txt'], [ r.fn for r in rv ] )
        self.assertEqual( ["x/a.txt","x/b.txt","y/c.txt","y/d.txt"], [ r.origfn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )

    def test_singlefile(self):
        rv = list( check_hashes(match_hashes(sumsrc=self.sumfile1[0:1], paths=self.td1/'a.txt')) )
        self.assertEqual( [self.td1/'a.txt'], [ r.fn for r in rv ] )
        self.assertEqual( ["a.txt"], [ r.origfn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )

    def test_dupesuminput(self):
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1*2, paths=self.td1)), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )
    def test_dupedirinput(self):
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1, paths=(self.td1, self.td1))), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )
    def test_dupeinput(self):
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1*2, paths=(self.td1, self.td1))), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )

    def test_multidirs(self):
        rv = sorted( check_hashes(match_hashes( sumsrc=self.sumfile2a + self.sumfile2b, paths=[self.td2/'x', self.td2/'y'])), key=lambda _: _.fn.name )
        self.assertEqual( [self.td2/'x'/'a.txt',self.td2/'x'/'b.txt',self.td2/'y'/'c.txt',self.td2/'y'/'d.txt'], [ r.fn for r in rv ] )
        self.assertEqual( ["x/a.txt","x/b.txt","y/c.txt","y/d.txt"], [ r.origfn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )
    def test_multifiles(self):
        rv = sorted( check_hashes(match_hashes( sumsrc=self.sumfile2a + self.sumfile2b, paths=self.td2 )), key=lambda _: _.fn.name )
        self.assertEqual( [self.td2/'x'/'a.txt',self.td2/'x'/'b.txt',self.td2/'y'/'c.txt',self.td2/'y'/'d.txt']
            + ([self.symlink] if self.symlink else []), [ r.fn for r in rv ] )
        self.assertEqual( ["x/a.txt","x/b.txt","y/c.txt","y/d.txt"]
            + ([str(self.symlink)] if self.symlink else []), [ r.origfn for r in rv ] )
        self.assertEqual( [ResultCode.SUMOK] * 4 + ([ResultCode.SKIP] if self.symlink else []), [r.code for r in rv])

    def test_badsum(self):
        with open(self.td1/"a.txt", "w", encoding="ASCII") as fh: print("AAAAa", file=fh, end="")
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1, paths=self.td1)), key=lambda _: _.fn.name )
        self.assertEqual( ["a.txt","b.txt","c.txt","d.txt"], [ r.fn.name for r in rv ] )
        self.assertEqual( rv[0].code, ResultCode.SUMMISMATCH )
        self.assertEqual( rv[0].msg, "checksum mismatch, calculated 81f56f825dff0cbcc1e0d42e14d88fa3, expected f6a6263167c92de8644ac998b3c4e4d1" )
        for i in range(1,4): self.assertEqual( rv[i].code, ResultCode.SUMOK )

    def test_missing(self):
        with open(self.td1/"f.txt", "w", encoding="ASCII") as fh: print("FFFFFFFFFF", file=fh, end="")
        sumfile3 = self.sumfile1 + (HashedFile.from_line("314a58a6ed7b845bd5e5e12ad86fad4c268d721fe265ad9f6e54150c89c95bff *./e.txt"),)
        rv = sorted( check_hashes(match_hashes(sumsrc=sumfile3, paths=self.td1)), key=lambda _: _.fn.name )
        self.assertEqual( ["a.txt","b.txt","c.txt","d.txt","e.txt","f.txt"], [ r.fn.name for r in rv ] )
        self.assertEqual( [ResultCode.SUMOK] * 4 + [ResultCode.MISSING, ResultCode.NOSUM], [ r.code for r in rv ] )

    def test_badinput(self):
        sumfile3 = self.sumfile1 + (HashedFile.from_line("f6a6263167c92de8644ac998b3c4e4d2 *a.txt"),)
        rv = sorted( check_hashes(match_hashes(sumsrc=sumfile3, paths=self.td1)), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertEqual( [ResultCode.BADINPUT, ResultCode.UNKNOWN] + [ResultCode.SUMOK] * 3, [ r.code for r in rv ] )
        self.assertEqual( rv[0].msg, "file appears more than once with differing checksums (f6a6263167c92de8644ac998b3c4e4d1 vs. f6a6263167c92de8644ac998b3c4e4d2)" )
        self.assertEqual( rv[1].msg, "can't reliably checksum file because it appears more than once in input" )
    def test_badinput_missing(self):
        sumfile3 = self.sumfile1 + (HashedFile.from_line("8b1a9953c4611296a827abf8c47804d7 *i.txt"),
                                    HashedFile.from_line("f5a7924e621e84c9280a9a27e1bcb7f6 *i.txt"))
        rv = sorted( check_hashes(match_hashes(sumsrc=sumfile3, paths=self.td1)), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt","i.txt","i.txt")], [ r.fn for r in rv ] )
        # this results in two "MISSING" reports because that is checked before duplicate filenames with differing hashes
        self.assertEqual( [ResultCode.SUMOK]*4 + [ResultCode.MISSING]*2, [ r.code for r in rv ] )

    def test_ignpath(self):
        (self.td2/'x'/'a.txt').rename(self.td2/'y'/'a.txt')
        # first, without the option to see the error
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile2a + self.sumfile2b, paths=self.td2)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/"a.txt",self.td2/'x'/"b.txt",self.td2/'y'/"a.txt",self.td2/'y'/"c.txt",self.td2/'y'/"d.txt"],
                [ r.fn for r in rv ] )
        self.assertEqual( ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.MISSING,ResultCode.SUMOK,ResultCode.NOSUM,ResultCode.SUMOK,ResultCode.SUMOK],
                [ r.code for r in rv ] )
        # now with the option
        rv = sorted(check_hashes(match_hashes(sumsrc=self.sumfile2a + self.sumfile2b, paths=self.td2, ignorepath=True)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/"b.txt",self.td2/'y'/"a.txt",self.td2/'y'/"c.txt",self.td2/'y'/"d.txt"],
                [ r.fn for r in rv ] )
        self.assertEqual( ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK]*4, [ r.code for r in rv ] )
        # and again with sumfile1 which has no paths
        rv = sorted(check_hashes(match_hashes(sumsrc=self.sumfile1, paths=self.td2, ignorepath=True)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/"b.txt",self.td2/'y'/"a.txt",self.td2/'y'/"c.txt",self.td2/'y'/"d.txt"],
                [ r.fn for r in rv ] )
        self.assertEqual( ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK]*4, [ r.code for r in rv ] )
        # and again with td1
        rv = sorted(check_hashes(match_hashes(sumsrc=self.sumfile2a + self.sumfile2b, paths=self.td1, ignorepath=True)), key=lambda _: _.fn.name )
        self.assertEqual( [ self.td1/f for f in ("a.txt","b.txt","c.txt","d.txt")], [ r.fn for r in rv ] )
        self.assertTrue( all( r.code==ResultCode.SUMOK for r in rv ) )

    def test_ignpath_badsum(self):
        (self.td2/'y'/'d.txt').unlink()
        with open(self.td2/"x"/"d.txt", "w", encoding="ASCII") as fh: print("DDDDDDDd", file=fh, end="")
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile1, paths=self.td2, ignorepath=True)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/"a.txt",self.td2/'x'/"b.txt",self.td2/'x'/"d.txt",self.td2/'y'/"c.txt"],
                [ r.fn for r in rv ] )
        self.assertEqual( ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK]*2 + [ResultCode.SUMMISMATCH,ResultCode.SUMOK], [ r.code for r in rv ] )
        self.assertEqual( rv[-2].msg, "checksum mismatch, "
            "calculated 8434e5b8172d1ed1e34a166c184808b5ba435cffe16d65abb934f4e69250a1850d8a061e84a336bbec3e9cb5c516d7532039b0bd1709845eb387244ebdc996ee, "
            "expected 9e79b63d8057ed9491ea95a4afa02588dac66e229abd08e8a44866f15ce9381c25a78aa891238e808f711bcf3c89c3aa6480bba392208a5b8c5fe35db1ac87b7" )

    def test_ignpath_missing(self):
        with open(self.td2/"f.txt", "w", encoding="ASCII") as fh: print("FFFFFFFFFF", file=fh, end="")
        sumfile3 = self.sumfile1 + (HashedFile.from_line("314a58a6ed7b845bd5e5e12ad86fad4c268d721fe265ad9f6e54150c89c95bff *./e.txt"),)
        rv = sorted( check_hashes(match_hashes(sumsrc=sumfile3, paths=self.td2, ignorepath=True)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( [PurePath('e.txt'),self.td2/'f.txt'] + ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/"a.txt",self.td2/'x'/"b.txt",self.td2/'y'/"c.txt",self.td2/'y'/"d.txt"],
                [ r.fn for r in rv ] )
        self.assertEqual( [ResultCode.MISSING, ResultCode.NOSUM] + ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK]*4 , [ r.code for r in rv ] )

    def test_ignpath_copy(self):
        shutil.copy(self.td2/'x'/'a.txt', self.td2/'y'/'a.txt')
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile2a + self.sumfile2b
            + (HashedFile.from_line("f6a6263167c92de8644ac998b3c4e4d1 *y/a.txt"),),
            paths=self.td2, ignorepath=True)), key=lambda _: (_.fn.parts[-2:], _.code) )
        self.assertEqual( [PurePath('a.txt'), PurePath('a.txt')] + ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/'b.txt', self.td2/'y'/'c.txt', self.td2/'y'/'d.txt'],
                [ r.fn for r in rv ])
        self.assertEqual( [ResultCode.DUPEFN, ResultCode.UNKNOWN] + ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK] + [ResultCode.SUMOK]*2, [ r.code for r in rv ] )
        self.assertTrue( rv[0].msg.startswith("filename appears more than once ") )

    def test_ignpath_badinput(self):
        sumfile3 = self.sumfile2a + self.sumfile2b + (HashedFile.from_line("f6a6263167c92de8644ac998b3c4e4d2 *y/a.txt"),)
        rv = sorted( check_hashes(match_hashes(sumsrc=sumfile3, paths=self.td2, ignorepath=True)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( [PurePath('a.txt'), PurePath('a.txt')] + ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/'b.txt', self.td2/'y'/'c.txt', self.td2/'y'/'d.txt'],
                [ r.fn for r in rv ])
        self.assertEqual( [ResultCode.BADINPUT, ResultCode.UNKNOWN] + ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK]*3, [ r.code for r in rv ] )
        self.assertEqual(rv[1].msg,
            "can't reliably checksum file because it appears more than once in input")
        self.assertEqual(rv[0].msg, "file appears more than once with differing checksums "
            "(f6a6263167c92de8644ac998b3c4e4d1 vs. f6a6263167c92de8644ac998b3c4e4d2)")
    def test_ignpath_badinput_missing(self):
        sumfile3 = self.sumfile2a + self.sumfile2b + (HashedFile.from_line("8b1a9953c4611296a827abf8c47804d7 *y/i.txt"),
                                                      HashedFile.from_line("f5a7924e621e84c9280a9a27e1bcb7f6 *y/i.txt"))
        rv = sorted( check_hashes(match_hashes(sumsrc=sumfile3, paths=self.td2, ignorepath=True)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( [PurePath('i.txt'), PurePath('i.txt')] + ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/'a.txt', self.td2/'x'/'b.txt', self.td2/'y'/'c.txt', self.td2/'y'/'d.txt'],
                [ r.fn for r in rv ])
        self.assertEqual( [ResultCode.BADINPUT, ResultCode.MISSING] + ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK]*4, [ r.code for r in rv ] )

    def test_ignpath_mismatch(self):
        with open(self.td2/"x"/"c.txt", "w", encoding="ASCII") as fh: print("CCCCCCc", file=fh, end="")
        rv = sorted( check_hashes(match_hashes(sumsrc=self.sumfile2a + self.sumfile2b, paths=self.td2, ignorepath=True)), key=lambda _: _.fn.parts[-2:] )
        self.assertEqual( [PurePath('c.txt'), PurePath('c.txt')] + ([self.symlink] if self.symlink else [])
            + [self.td2/'x'/'a.txt', self.td2/'x'/'b.txt', self.td2/'y'/'d.txt'],
                [ r.fn for r in rv ])
        self.assertEqual( [ResultCode.DUPEFN, ResultCode.UNKNOWN] + ([ResultCode.SKIP] if self.symlink else [])
            + [ResultCode.SUMOK, ResultCode.SUMOK, ResultCode.SUMOK],
                [ r.code for r in rv ] )

    def test_errs(self):
        with self.assertRaises(ValueError): set(match_hashes(sumsrc=[], paths=[]))

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
