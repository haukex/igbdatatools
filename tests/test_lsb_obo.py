#!/usr/bin/env python
"""Tests for lsb_obo.

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
from lsb_obo import lsb_obo

tests_valid = (
    ('1010.82',  '1010.821'),
    ('1035.427', '1035.428'),
    ('1035.349', '1035.35' ),
    ('1035.1',   '1035.101'),
    ('1035.1',   '1035.099'),
    ('1033.948', '1033.949'),
    ('1026.225', '1026.226'),
    ('1026.439', '1026.44' ),
    ('1031.599', '1031.6'  ),
    ('1023.819', '1023.82' ),
    ('1028',     '1028.001'),
    ('1012.999', '1013'    ),
    ('999.9999', '1000'    ),
    ('0.08789861', '0.08789862'),
    ('0.06854691', '0.0685469' ),
    ('0.07948849', '0.0794885' ),
    ('0.04322401', '0.04322402'),
    ('0.03839611', '0.0383961' ),
    ('0.05854917', '0.05854916'),
    ('0.05091807', '0.05091806'),
)
tests_invalid = (
    ('1035.426', '1035.428'),
    ('1035.1',   '1035.102'),
    ('1035.1',   '1035.110'),
    ('0.05854917', '0.05754916'),
)
tests_error = (
    ('1035.',    '1035.101'),
    (' 1010.82', '1010.821'),
    ('1035.349', '1035x' ),
    ('1035.1',   ''),
    ( '.05854917', '0.05854916'),
)

class TestLsbObo(unittest.TestCase):

    def test_lsb_obo(self):
        for a,b in tests_valid:
            self.assertTrue( lsb_obo(a,b) )
        for a,b in tests_invalid:
            self.assertFalse( lsb_obo(a,b) )
        for a,b in tests_error:
            with self.assertRaises(ValueError):
                lsb_obo(a,b)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
