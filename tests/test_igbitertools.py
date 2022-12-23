#!/usr/bin/env python3
"""Tests for igbitertools.

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
from igbitertools import gray_product, no_duplicates
from itertools import product

class TestIgbItertools(unittest.TestCase):

    def test_gray_product(self):
        self.assertEqual( tuple( gray_product( ('a','b','c'), range(1,3) ) ),
            ( ("a",1), ("b",1), ("c",1), ("c",2), ("b",2), ("a",2) ) )

        out = gray_product(('foo', 'bar'), (3, 4, 5, 6), ['quz', 'baz'])
        self.assertEqual(next(out), ('foo', 3, 'quz'))
        self.assertEqual(list(out), [
            ('bar', 3, 'quz'), ('bar', 4, 'quz'), ('foo', 4, 'quz'), ('foo', 5, 'quz'), ('bar', 5, 'quz'),
            ('bar', 6, 'quz'), ('foo', 6, 'quz'), ('foo', 6, 'baz'), ('bar', 6, 'baz'), ('bar', 5, 'baz'),
            ('foo', 5, 'baz'), ('foo', 4, 'baz'), ('bar', 4, 'baz'), ('bar', 3, 'baz'), ('foo', 3, 'baz')])

        self.assertEqual( tuple( gray_product() ), ((), ) )
        self.assertEqual( tuple( gray_product( (1,2) ) ), ( (1,), (2,) ) )
        with self.assertRaises(ValueError): list( gray_product( (1,2), () ) )
        with self.assertRaises(ValueError): list( gray_product( (1,2), (2,) ) )

        iters = ( ("a","b"), range(3,6), [None, None], {"i","j","k","l"}, "XYZ" )
        self.assertEqual( sorted( product(*iters) ), sorted( gray_product(*iters) ) )

    def test_no_duplicates(self):
        in1 = ( "foo", "bar", "quz", 123 )
        self.assertEqual( tuple(no_duplicates(in1)), in1 )
        in2 = [ "foo", ["bar", "quz"] ]
        self.assertEqual( list(no_duplicates(in2)), in2 )
        with self.assertRaises(ValueError):
            tuple(no_duplicates( ("foo", 123, "bar", "foo") ))
        with self.assertRaises(ValueError):
            set(no_duplicates( ("foo", "bar", "quz", "Foo"), key=str.lower ))
        with self.assertRaises(ValueError):
            list(no_duplicates( [ ["foo","bar"], "quz", ["baz"], ["foo","bar"] ] ))

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
