#!/usr/bin/env python
"""Tests for deltaparse.

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
from deltaparse import deltaparse

class TestDeltaParse(unittest.TestCase):

    def test_deltaparse(self):
        self.assertEqual( deltaparse("123"), 123 )
        self.assertEqual( deltaparse("567s"), 567 )
        self.assertEqual( deltaparse("5m"), 300 )
        self.assertEqual( deltaparse("0s 5m 0d 0h 0d"), 300 )
        self.assertEqual( deltaparse("7h"), 25200 )
        self.assertEqual( deltaparse("3d"), 259200 )
        self.assertEqual( deltaparse("2d5h12m32s"), 191552 )
        self.assertEqual( deltaparse("2D5H12M32S"), 191552 )
        self.assertEqual( deltaparse("0"), 0 )
        self.assertEqual( deltaparse(" "), 0 )
        self.assertEqual( deltaparse("0d0h0m0s"), 0 )
        self.assertEqual( deltaparse(" 2 d 5 h 12 m 32 s"), 191552 )
        self.assertEqual( deltaparse("40 5d 3h 2d 2s"), 615642 )
        self.assertEqual( deltaparse("7d 3h 42s"), 615642 )
        with self.assertRaises(ValueError): deltaparse("-3d")
        with self.assertRaises(ValueError): deltaparse("5hours")
        with self.assertRaises(ValueError): deltaparse("5x")
        with self.assertRaises(ValueError): deltaparse("5m m")
        with self.assertRaises(ValueError): deltaparse("x")

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
