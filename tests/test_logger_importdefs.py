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
from igbpyutils.test import tempcopy
from dataclasses import replace
from datetime import datetime
import numpy
from loggerdata.metadata import load_logger_metadata
from loggerdata.importdefs import Record, DataFileType, RecordError

class TestLoggerDataImportDefs(unittest.TestCase):

    md = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":'
        b'{"prikey":0,"columns":[ {"name":"Hello"}, {"name":"World"}, {"name":"Foo"}, {"name":"Bar"}, {"name":"Quz"} ],'
        b'"mappings":{"xy":{"type":"view","map":[{"old":{"name":"Foo"},"new":{"name":"xyz"}}]}} }}}')

    def test_record_row(self):
        self.assertEqual( Record(origrow=("abc","def"), tblmd=self.md.tables['foo'], variant=(1,3),
                                 filenames=(), srcline=1, filetype=DataFileType.TOA5).fullrow,
                          (None,"abc",None,"def",None) )
        with self.assertRaises(RecordError):
            _ = Record(origrow=("abc","def"), tblmd=self.md.tables['foo'], variant=(0,1,3),
                       filenames=(), srcline=1, filetype=DataFileType.TOA5).fullrow

    def test_record_source(self):
        rec = Record(origrow=(), tblmd=self.md.tables['foo'], variant=(),
            filenames=("foo.zip","bar.csv"), srcline=42, filetype=DataFileType.TOA5)
        self.assertEqual( rec.source, "('foo.zip', 'bar.csv'):42" )
        self.assertEqual( replace(rec, filenames=('bar.csv',)).source, "bar.csv:42" )
        self.assertEqual( replace(rec, filenames='bar.csv').source, "bar.csv:42" )

    def test_record_fullrow_as_py_np(self):
        with self.assertWarns(UserWarning):
            md2 = load_logger_metadata(b'{"logger_name":"Bar","toa5_env_match":{"station_name":"Bar"},"tz":"-03:30","tables":{"bar":'
                b'{"prikey":0,"columns":[ {"name":"Hello","type":"TimestampNoTz"}, {"name":"xyz"}, {"name":"World","type":"TimestampWithTz"}, {"name":"iii","type":"NonNegInt"} ]}}}')
        with self.assertRaises(ValueError):
            Record(origrow=("2023-01-02 03:04:05","","2023-01-02 03:04:56+04:3","42"), tblmd=md2.tables['bar'],
                   variant=(0,1,2,3), filenames=(), srcline=3, filetype=DataFileType.TOA5).typecheck()
        rec = Record(origrow=("2023-01-02 03:04:05","","2023-01-02 03:04:56+04:30","42"), tblmd=md2.tables['bar'],
                     variant=(0,1,2,3), filenames=(), srcline=3, filetype=DataFileType.TOA5).typecheck()
        self.assertEqual( tuple(rec.fullrow_as_py()), (datetime.fromisoformat("2023-01-02 06:34:05Z"),"",datetime.fromisoformat("2023-01-01 22:34:56Z"),42) )
        with self.assertRaises(TypeError):
            tuple(rec.fullrow_as_np())
        with self.assertWarns(UserWarning):
            md3 = load_logger_metadata(b'{"logger_name":"Quz","toa5_env_match":{"station_name":"Quz"},"tz":"Europe/Berlin","tables":{"quz":'
                b'{"columns":[ {"name":"TIMESTAMP","unit":"TS","type":"TimestampNoTz"}, {"name":"Other","type":"TimestampWithTz"},'
                b'{"name":"iii","type":"NonNegInt"}, {"name":"jjj","type":"BigInt"} ]}}}')
        rec2 = Record(origrow=("2022-12-01 14:00:00","2021-06-18 14:00:00 -10:00","42","-5624536"), tblmd=md3.tables['quz'],
                      variant=(0,1,2,3), filenames=(), srcline=5, filetype=DataFileType.TOA5).typecheck()
        self.assertEqual( tuple(rec2.fullrow_as_py()), (datetime.fromisoformat("2022-12-01 13:00:00Z"),datetime.fromisoformat("2021-06-19 00:00:00Z"),42,-5624536) )
        self.assertEqual( tuple(rec2.fullrow_as_np()), (numpy.datetime64("2022-12-01 13:00:00"),numpy.datetime64("2021-06-19 00:00:00"),numpy.uint32(42),numpy.int64(-5624536)) )

    def test_record_view(self):
        rec = Record(origrow=("abc","def","ghi","jkl","mno"), tblmd=self.md.tables['foo'], variant=(0,1,2,3,4),
                     filenames=(), srcline=1, filetype=DataFileType.TOA5)
        self.assertEqual( tuple(rec.view('xy')), ("ghi",) )
        with tempcopy(self.md) as md2:
            md2.tables['foo'].mappings['xy'].type = None
            with self.assertRaises(TypeError):
                tuple( replace(rec, tblmd=md2.tables['foo']).view('xy') )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
