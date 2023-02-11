#!/usr/bin/env python3
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
from dataclasses import replace
from loggerdata.metadata import load_logger_metadata
from loggerdata.importdefs import Record, DataFileType, RecordError

class TestLoggerDataImportDefs(unittest.TestCase):

    md = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":'
        b'{"prikey":0,"columns":[ {"name":"Hello"}, {"name":"World"}, {"name":"Foo"}, {"name":"Bar"}, {"name":"Quz"} ]}}}')

    def test_record_row(self):
        self.assertEqual( Record(origrow=("abc","def"), tblmd=self.md.tables['foo'], variant=(1,3),
                                 filenames=(), srcline=1, filetype=DataFileType.CSV).row,
                          (None,"abc",None,"def",None) )
        with self.assertRaises(RecordError):
            _ = Record(origrow=("abc","def"), tblmd=self.md.tables['foo'], variant=(0,1,3),
                       filenames=(), srcline=1, filetype=DataFileType.CSV).row

    def test_record_source(self):
        rec = Record(origrow=(), tblmd=self.md.tables['foo'], variant=(),
            filenames=("foo.zip","bar.csv"), srcline=42, filetype=DataFileType.CSV)
        self.assertEqual( rec.source, "('foo.zip', 'bar.csv'):42" )
        self.assertEqual( replace(rec, filenames=('bar.csv',)).source, "bar.csv:42" )
        self.assertEqual( replace(rec, filenames='bar.csv').source, "bar.csv:42" )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
