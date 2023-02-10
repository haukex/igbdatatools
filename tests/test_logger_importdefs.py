#!/usr/bin/env python3c
"""Tests for loggerdata.importdefs

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
from loggerdata.importdefs import Record, RecordContext, DataFileType

class TestLoggerDataImportDefs(unittest.TestCase):

    def test_record_source(self):
        # noinspection PyTypeChecker
        rec = Record(row=(), tblmd=None, variant=(), ctx=RecordContext(),
            filenames=("foo.zip","bar.csv"), srcline=42, filetype=DataFileType.CSV)
        self.assertEqual( rec.source, "('foo.zip', 'bar.csv'):42" )
        self.assertEqual( rec._replace(filenames=('bar.csv',)).source, "bar.csv:42" )
        self.assertEqual( rec._replace(filenames='bar.csv').source, "bar.csv:42" )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
