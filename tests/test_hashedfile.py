#!/usr/bin/env python3
"""Tests for hashedfile library.

Author, Copyright, and License
------------------------------
Copyright (c) 2022-2023 Hauke Daempfling (haukex@zero-g.net)
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
import hashlib
from pathlib import Path, PurePath
from tempfile import TemporaryDirectory
from hashedfile import HashedFile, hashes_to_file, hashes_from_file, DEFAULT_HASH, sort_hashedfiles, SortingType
from igbpyutils.file import NamedTempFileDeleteLater

class TestHashedFile(unittest.TestCase):

    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.temppath = Path(self.tempdir.name)
        ( tdx := self.temppath/'x' ).mkdir()
        ( tdy := self.temppath/'y' ).mkdir()
        def mkfile(fn: PurePath, content: bytes, hsh: str):
            with open(fn, 'wb') as fh: fh.write(content)
            return f"{hsh} *{fn.relative_to(self.temppath)}"
        self.sumfile_lines = (
            # MD5, SHA1, SHA256, and SHA512
            mkfile( tdx/'a.txt', b"AAAAA",    "f6a6263167c92de8644ac998b3c4e4d1" ),
            mkfile( tdx/'b.txt', b"BBBBBB",   "25363e98eb50cc813f0d3eff743f34908419b557" ),
            mkfile( tdy/'c.txt', b"CCCCCCC",  "d1cf7fb693b553eeca55dc40f1e93af6e89b7fd803c2f7e689aab4ca16257d0a" ),
            mkfile( tdy/'d.txt', b"DDDDDDDD", "9e79b63d8057ed9491ea95a4afa02588dac66e229abd08e8a44866f15ce9381c25a78aa8"
                                              "91238e808f711bcf3c89c3aa6480bba392208a5b8c5fe35db1ac87b7"),
        )
        self.sumfile256lines = (
            f"11770b3ea657fe68cba19675143e4715c8de9d763d3c21a85af6b7513d43997d *{Path('x','a.txt')}",
            f"9d9816fe3f392fcf547d886a4f2d635adf86cbda3e9d8f5e687e42188160ec6d *{Path('x','b.txt')}",
            f"d1cf7fb693b553eeca55dc40f1e93af6e89b7fd803c2f7e689aab4ca16257d0a *{Path('y','c.txt')}",
            f"b1eedd29abf7e8b9b5c67030fc59dd42a4e16a0585c26176de357a4757515ed6 *{Path('y','d.txt')}",
        )

    def tearDown(self):
        self.tempdir.cleanup()
        self.tempdir = None
        self.temppath = None

    def test_hashedfile(self):
        file = self.temppath/'x'/'a.txt'
        hsh = bytes.fromhex('232d43e52834558e9457b0901ee65c86196bf8777c8ff4fc61fdd5e69fd1d24f964fed1bf481b6ef52a69d1737'
                            '2554fecb098fb07f839e64916bdd0d2abf018a')
        badhsh = bytes.fromhex('332d43e52834558e9457b0901ee65c86196bf8777c8ff4fc61fdd5e69fd1d24f964fed1bf481b6ef52a69d1'
                               '7372554fecb098fb07f839e64916bdd0d2abf018a')
        line       = hsh.hex() + " *" + str(file)
        line_nobin = hsh.hex() + "  " + str(file)
        line_rel   = hsh.hex() + " *" + os.path.join('x','a.txt')
        hf1 = HashedFile.from_file(file)
        self.assertIs( hf1.fn, file )
        self.assertEqual( hf1.hsh, hsh )
        self.assertTrue( hf1.valid )
        self.assertTrue( hf1.binflag )
        self.assertIs( hf1.algo, DEFAULT_HASH )
        self.assertIs( hf1.validate(), hf1 )
        self.assertIsNot( hf1.validate(force=True), hf1 )
        self.assertEqual( hf1.to_line(), line )
        self.assertEqual( hf1.setfn( os.path.relpath(hf1.fn, self.temppath) ).to_line(), line_rel )
        hf2 = HashedFile.from_line(line)
        self.assertEqual( hf1, hf2 )
        self.assertTrue( hf1==hf2 )
        self.assertFalse( hf1!=hf2 )
        self.assertIsNone( hf2.valid )
        self.assertTrue( hf2.binflag )
        self.assertEqual( hf2.to_line(), line )
        self.assertFalse( HashedFile.from_line(line_nobin).binflag )
        hf2v = hf2.validate()
        self.assertIsNot( hf2, hf2v )
        self.assertEqual( hf2, hf2v )
        self.assertTrue( hf2v.valid )
        self.assertTrue( hf2v.binflag )
        hf2vs, actualhsh = hf2.validate(fail_soft=True)
        self.assertIsNot( hf2, hf2vs )
        self.assertEqual( hf2, hf2vs )
        self.assertEqual( hf2.hsh, actualhsh )
        self.assertTrue( hf2vs.valid )
        self.assertTrue( hf2vs.binflag )
        hf2vs2, actualhsh2 = hf2vs.validate(fail_soft=True)
        self.assertIs( hf2vs, hf2vs2 )
        self.assertEqual( hf2vs2.hsh, hf2.hsh )
        bag = { hf1, hf2 }
        self.assertEqual( len(bag), 1 )
        self.assertEqual( bag.pop(), hf2v )
        with self.assertRaises(ValueError) as ctx: HashedFile.from_line("abcdefg *foo.txt")
        self.assertEqual( str(ctx.exception), "failed to parse line 'abcdefg *foo.txt'" )
        hf3 = HashedFile( fn=file, hsh=badhsh )
        self.assertIsNone( hf3.valid )
        with self.assertRaises(ValueError) as ctx: hf3.validate()
        self.assertEqual( str(ctx.exception), f"failed to validate {file}: expected {badhsh.hex()}, got {hsh.hex()}" )
        hf3v, actualhsh2 = hf3.validate(fail_soft=True)
        self.assertIsNot( hf3v, hf3 )
        self.assertEqual( hf3v, hf3 )
        self.assertEqual( actualhsh2, hsh )
        self.assertIsNotNone( hf3v.valid )
        self.assertFalse( hf3v.valid )
        self.assertEqual( hf3v.rehash(), hf1 )
        with self.assertRaises(ValueError) as ctx: HashedFile.from_line("abcdef *foo.txt")
        self.assertEqual( str(ctx.exception), "hash has unknown length: b'\\xab\\xcd\\xef'" )
        # NOTE the following test requires that there *isn't* a file named "x" in the pwd
        with self.assertRaises(FileNotFoundError): HashedFile.from_line(line_rel).validate()
        hf4 = HashedFile.from_line(line_rel)
        hf4 = hf4.setfn( os.path.join(self.temppath, hf4.fn) )
        self.assertEqual( hf1, hf4.validate() )
        hf5 = HashedFile.from_file( file, algo=hashlib.sha1 )
        self.assertNotEqual( hf5, hf1 )
        self.assertEqual( hf5.fn, hf1.fn )
        self.assertNotEqual( hf5.hsh, hf1.hsh )
        self.assertEqual( hf5.hsh, bytes.fromhex('c1fe3a7b487f66a6ac8c7e4794bc55c31b0ef403') )
        self.assertEqual( hf5.rehash().hsh, bytes.fromhex('c1fe3a7b487f66a6ac8c7e4794bc55c31b0ef403') )
        self.assertEqual( hf5.rehash(algo=DEFAULT_HASH), hf1 )
        # cover _algo_from_hashsize:
        self.assertEqual( hashlib.sha384, HashedFile.from_line("1d283e09aa7e597f2c0505c13f7c09eb4d4cd198fb7b144eeea2824cc59a046d9363b3f038abf7aa6bde7f8adaf561a4 *x").algo )
        self.assertEqual( hashlib.sha224, HashedFile.from_line("acbe28e133c6e7e8cc740d5c70875c995e0b5950aa010b25649eb540 *x").algo )

    def test_hashfiles(self):
        hashes = [ HashedFile.from_file(f) for f in self.temppath.rglob('*') if f.is_file() ]
        self.assertTrue( all( h.valid for h in hashes ) )
        self.assertTrue( all( h.algo is DEFAULT_HASH for h in hashes ) )

    def test_hashlines(self):
        hashes = [ HashedFile.from_line(h) for h in self.sumfile_lines ]
        self.assertIs( hashes[0].algo, hashlib.md5 )
        self.assertIs( hashes[1].algo, hashlib.sha1 )
        self.assertIs( hashes[2].algo, hashlib.sha256 )
        self.assertIs( hashes[3].algo, hashlib.sha512 )
        self.assertTrue( all( not h.valid for h in hashes ) )
        self.assertTrue( all( h.setfn( os.path.join(self.temppath, h.fn) ).validate().valid for h in hashes ) )

    def test_to_from_file(self):
        hsh1 = [ HashedFile.from_file(f, algo=hashlib.sha256).setfn( f.relative_to(self.temppath) )
                 for f in self.temppath.rglob('*') if f.is_file() ]
        with NamedTempFileDeleteLater() as tf:
            tf.close()
            # write the hashes to the file
            cnt = hashes_to_file(tf.name, hsh1)
            self.assertEqual(cnt, 4)
            # read the lines back out and check them
            with open(tf.name, encoding='UTF-8') as fh:
                lines = [ ln.rstrip("\r\n") for ln in fh ]
            self.assertEqual( sorted(self.sumfile256lines), sorted(lines) )
            # read the file back in
            hsh2 = list(hashes_from_file(tf.name))
            self.assertEqual(hsh1, hsh2)

    def test_sort_hashedfiles(self):
        lines = (
            "f6a6263167c92de8644ac998b3c4e4d1 *baz.txt",
            "f6a6263167c92de8644ac998b3c4e4d1  quz.txt",
            "fa0903293ec8fc1f19087d0eb2ffded8 *bar.txt",
            "f6a6263167c92de8644ac998b3c4e4d1 *bla.txt",
            "c36e60f574001ef3de0a551f950bdb39 *foo.txt" )
        self.assertEqual( sorted(lines), [
            "c36e60f574001ef3de0a551f950bdb39 *foo.txt",
            "f6a6263167c92de8644ac998b3c4e4d1  quz.txt",
            "f6a6263167c92de8644ac998b3c4e4d1 *baz.txt",
            "f6a6263167c92de8644ac998b3c4e4d1 *bla.txt",
            "fa0903293ec8fc1f19087d0eb2ffded8 *bar.txt" ] )
        samp = tuple(map(HashedFile.from_line, lines))
        self.assertEqual( list(sort_hashedfiles(samp, SortingType.NO_SORT)),
            list(samp) )
        self.assertEqual( list(sort_hashedfiles(samp, SortingType.BY_LINE)),
            list(map(HashedFile.from_line, (
                "c36e60f574001ef3de0a551f950bdb39 *foo.txt",
                "f6a6263167c92de8644ac998b3c4e4d1 *baz.txt",
                "f6a6263167c92de8644ac998b3c4e4d1 *bla.txt",
                "f6a6263167c92de8644ac998b3c4e4d1  quz.txt",
                "fa0903293ec8fc1f19087d0eb2ffded8 *bar.txt" ))) )
        self.assertEqual( list(sort_hashedfiles(samp, SortingType.BY_HASH)),
            list(map(HashedFile.from_line, (
                "c36e60f574001ef3de0a551f950bdb39 *foo.txt",
                "f6a6263167c92de8644ac998b3c4e4d1 *baz.txt",
                "f6a6263167c92de8644ac998b3c4e4d1  quz.txt",
                "f6a6263167c92de8644ac998b3c4e4d1 *bla.txt",
                "fa0903293ec8fc1f19087d0eb2ffded8 *bar.txt" ))) )
        self.assertEqual( list(sort_hashedfiles(samp, SortingType.BY_FILE)),
            list(map(HashedFile.from_line, (
                "fa0903293ec8fc1f19087d0eb2ffded8 *bar.txt",
                "f6a6263167c92de8644ac998b3c4e4d1 *baz.txt",
                "f6a6263167c92de8644ac998b3c4e4d1 *bla.txt",
                "c36e60f574001ef3de0a551f950bdb39 *foo.txt",
                "f6a6263167c92de8644ac998b3c4e4d1  quz.txt" ))) )
        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            list(sort_hashedfiles(samp, None))

    def test_sorted_gen(self):
        """Test for a statement in the documentation of ``sort_hashedfiles``."""
        ops = []
        def foo():
            for x in (5,2,9,0,1,6,4,3,8,7):
                ops.append('yield')
                yield x
        def bar(inp):
            ops.append('bar')
            yield from sorted(inp)
        ops.append('one')
        one = foo()
        ops.append('two')
        two = bar(one)
        ops.append('three')
        three = list(two)
        ops.append('four')
        self.assertEqual( three, list(range(10)) )
        self.assertEqual( ops, ['one', 'two', 'three', 'bar'] + ['yield']*10 + ['four'] )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
