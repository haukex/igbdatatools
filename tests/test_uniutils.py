#!/usr/bin/env python
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
from itertools import product, chain
# noinspection PyPackageRequirements
from icu import UnicodeString
from uniutils import graphemeclusters, is_common_ascii_char, format_unichars, try_encodings, ControlCharReport, DEFAULT_ENCODINGS

class TestUniUtils(unittest.TestCase):

    def test_graphemeclusters(self):
        self.assertEqual( tuple(graphemeclusters("")), () )
        self.assertEqual( tuple(graphemeclusters("ABC")), ("A","B","C") )
        self.assertEqual( tuple(graphemeclusters(UnicodeString("ABC"))), ("A","B","C") )
        text = "äBéÇ 각நி-æ\r\n"
        exp = ("a\N{COMBINING DIAERESIS}","B","e\N{COMBINING ACUTE ACCENT}","C\N{COMBINING CEDILLA}"," ",
            "\N{HANGUL CHOSEONG KIYEOK}\N{HANGUL JUNGSEONG A}\N{HANGUL JONGSEONG KIYEOK}",
            "\N{TAMIL LETTER NA}\N{TAMIL VOWEL SIGN I}","-","\N{LATIN SMALL LETTER AE}",
            "\N{CARRIAGE RETURN}\N{LINE FEED}")
        self.assertEqual( tuple(graphemeclusters(text)), exp )

    def test_is_common_ascii_char(self):
        self.assertTrue( is_common_ascii_char("A") )
        self.assertTrue( is_common_ascii_char("\x0D\x0A") )
        self.assertFalse( is_common_ascii_char("O\N{COMBINING DIAERESIS}") )
        self.assertFalse( is_common_ascii_char("\N{LATIN SMALL LETTER AE}") )

    def test_format_unichars(self):
        self.assertEqual(format_unichars("A"), "U+0041 LATIN CAPITAL LETTER A")
        self.assertEqual(format_unichars("a\N{COMBINING DIAERESIS}"),
            "U+0061 LATIN SMALL LETTER A + U+0308 COMBINING DIAERESIS")

    def test_try_encodings(self):
        self.assertEqual( tuple(try_encodings(b'Hello, World!\n')), DEFAULT_ENCODINGS )
        unitxt = "H∃llⓄ, 🗺!\n".encode('UTF-8')
        with self.assertRaises(StopIteration): next(try_encodings(unitxt, encodings=["ASCII"]))
        self.assertEqual(list(try_encodings(unitxt)), ["UTF-8", "ISO-8859-1", "CP1252"])
        self.assertEqual(
            list(try_encodings("a\N{COMBINING DIAERESIS}".encode("UTF-8"))),
            ["UTF-8","ISO-8859-1","CP1252"] )
        self.assertEqual(
            list(try_encodings("a\N{COMBINING DIAERESIS}e\N{COMBINING ACUTE ACCENT}".encode("UTF-8"))),
            ["UTF-8","ISO-8859-1"] )

    def test_control_char_report(self):
        crlf = ''.join( ''.join(p) for p in
            product( ("\x0D","\x0A","\x0D\x0A",""), ("\x0D","\x0A","\x0D\x0A",""), ('x',) ))
        rep1 = ControlCharReport.from_text(crlf)
        self.assertEqual( ControlCharReport(cr=7, lf=7, crlf=9, nul=0, ctrl=0), rep1 )
        self.assertEqual( "MIXED CR/LF, 7 CRs, 7 LFs, 9 CRLFs", str(rep1) )
        ctrls = ''.join( map(chr, chain(range(9),(10,11,12),range(14,32))) )
        rep2 = ControlCharReport.from_text(ctrls)
        self.assertEqual( ControlCharReport(cr=0, lf=1, crlf=0, nul=1, ctrl=28), rep2 )
        self.assertEqual( "1 NULs, 28 CTRLs (excl NUL/CR/LF/Tab), 1 LFs", str(rep2) )
        rep3 = ControlCharReport.from_text("abc")
        self.assertEqual( ControlCharReport(cr=0, lf=0, crlf=0, nul=0, ctrl=0), rep3 )
        self.assertEqual( "no CR or LF", str(rep3) )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
