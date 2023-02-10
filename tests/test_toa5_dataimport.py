#!/usr/bin/env python3
"""Tests for loggerdata.toa5.dataimport

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
from pathlib import Path
from contextlib import suppress
from more_itertools import unique_justseen, peekable
from testutils import tempcopy
from loggerdata.metadata import load_logger_metadata, ColumnHeader
from loggerdata.toa5 import EnvironmentLine
from loggerdata.toa5.dataimport import read_toa5_records, header_match
from loggerdata.importdefs import NoTableMatch, DataFileType, NoMetadataMatch, NoVariantMatch, RecordError

exp_metadata = [
    { "envline": EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger.CR1X", program_sig="2438", table_name="Daily" ), "variant":(0,1,2,3,4,5,6,7) },
    { "envline": EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger.CR1X", program_sig="2438", table_name="Hourly"), "variant":(0,1,2,3,4,5,7)  },
    { "envline": EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger.CR1X", program_sig="1234", table_name="Hourly"), "variant":(0,1,2,3,4,6,7,8) },
]

expect = {
    "Daily": [
        (("2021-06-19 00:00:00","0","12.99","2021-06-18 16:08:30","23.72","2021-06-19 00:00:00","39.16","2021-06-18 15:33:20"),exp_metadata[0]),
        (("2021-06-20 00:00:00","1","12.96","2021-06-19 13:13:05","21.54","2021-06-19 03:15:00","40.91","2021-06-19 14:04:15"),exp_metadata[0]),
        (("2021-06-21 00:00:00","2","12.97","2021-06-20 14:11:35","22.27","2021-06-20 03:27:05","39.99","2021-06-20 13:45:55"),exp_metadata[0]),
        (("2021-06-22 00:00:00","3","13.03","2021-06-21 16:00:15","20.45","2021-06-22 00:00:00","38.21","2021-06-21 14:47:35"),exp_metadata[0]),
        (("2021-06-23 00:00:00","4","13.54","2021-06-22 08:31:35","14.84","2021-06-23 00:00:00","23.69","2021-06-22 08:14:25"),exp_metadata[0]),
        (("2021-06-24 00:00:00","5","13.35","2021-06-23 15:51:20","12.92","2021-06-23 03:15:55","29.04","2021-06-23 11:42:15"),exp_metadata[0]),
    ],
    "Hourly": [
        (("2021-06-18 11:00:00", "0","13.11","35.3", "35.65","32.41",None,   "24.46",None      ),exp_metadata[1]),
        (("2021-06-18 12:00:00", "1","13.09","35.61","36.56","32.96",None,   "24",   None      ),exp_metadata[1]),
        (("2021-06-18 13:00:00", "2","13.06","36.56","37.42","33.47",None,   "24.35",None      ),exp_metadata[1]),
        (("2021-06-18 14:00:00", "3","13.02","37.42","38.6", "33.64",None,   "24.19",None      ),exp_metadata[1]),
        (("2021-06-18 15:00:00", "4","13",   "38.42","38.87","33.55",None,   "24.8", None      ),exp_metadata[1]),
        (("2021-06-18 16:00:00", "5","13",   "38.87","39.16","33.66",None,   "23.87",None      ),exp_metadata[1]),
        (("2021-06-18 17:00:00", "6","12.99","37.97","38.96","32.86",None,   "28.37",None      ),exp_metadata[1]),
        (("2021-06-18 18:00:00", "7","13.01","35.91","37.97","31.27",None,   "35.81",None      ),exp_metadata[1]),
        (("2021-06-18 19:00:00", "8","13.06","33.51","35.9", "29.74",None,   "40.61",None      ),exp_metadata[1]),
        (("2021-06-18 20:00:00", "9","13.14","30.82","33.51","27.96",None,   "45.66",None      ),exp_metadata[1]),
        (("2021-06-18 21:00:00","10","13.23","28.62","30.82","26.29",None,   "49.31",None      ),exp_metadata[1]),
        (("2021-06-18 22:00:00","11","13.31","27.14","28.62","25.14",None,   "54.85",None      ),exp_metadata[1]),
        (("2021-06-18 23:00:00","12","13.36","25.62","27.14","23.64",None,   "63.28",None      ),exp_metadata[1]),
        (("2021-06-19 00:00:00","13","13.42","23.72","25.61","21.47",None,   "81",   None      ),exp_metadata[1]),
        (("2021-06-19 01:00:00","14","13.51","22.05","23.72","19.67",None,   "100",  None      ),exp_metadata[1]),
        (("2021-06-19 02:00:00","15","13.56","21.66","22.05","20.79",None,   "76.63",None      ),exp_metadata[1]),
        (("2021-06-19 03:00:00","16","13.59","21.58","21.79","21.01",None,   "77.35",None      ),exp_metadata[1]),
        (("2021-06-19 04:00:00","17","13.59","21.54","22.41","20.83",None,   "77.53",None      ),exp_metadata[1]),
        (("2021-06-19 05:00:00","18","13.5", "22.41","25.52","22.45",None,   "69.93",None      ),exp_metadata[1]),
        (("2021-06-19 06:00:00","19","13.4", "25.53","28.4", "24.41",None,   "56.34",None      ),exp_metadata[1]),
        (("2021-06-19 07:00:00","20","13.33","28.41","30.83","26.35",None,   "50.1", None      ),exp_metadata[1]),
        (("2021-06-19 08:00:00","21","13.22","30.84","33.5", None,   "28.51","46.3", "1015.323"),exp_metadata[2]),
        (("2021-06-19 09:00:00","22","13.12","33.5", "36.14",None,   "30.62","37.51","1015.177"),exp_metadata[2]),
        (("2021-06-19 10:00:00","23","13.06","36.15","37.62",None,   "32.22","32.27","1014.946"),exp_metadata[2]),
        (("2021-06-19 11:00:00","24","13.03","37.62","38.44",None,   "33.61","27.29","1014.73" ),exp_metadata[2]),
        (("2021-06-19 12:00:00","25","13.01","38.44","39.09",None,   "34.17","27.22","1014.399"),exp_metadata[2]),
    ],
}

class TestToa5DataImport(unittest.TestCase):

    def test_read_toa5_records(self):
        self.maxDiff = None
        inpath = Path(__file__).parent/'toa5'
        metad = load_logger_metadata( Path(__file__).parent/'TestLogger.json' )
        got = { "Daily": [], "Hourly": [] }
        for file in ( f for f in inpath.iterdir() if f.suffix.lower() == '.dat' ):
            with file.open(encoding="ASCII", newline='') as fh:
                recsrc = peekable(read_toa5_records(fh, metadatas=metad, filenames=file))
                with suppress(NoTableMatch): recsrc.peek()
                for rec in recsrc:
                    # noinspection PyUnresolvedReferences
                    myrec = ( rec.row, { "envline": rec.ctx.envline, "variant": rec.variant } )
                    self.assertEqual(file, rec.filenames)
                    self.assertIs(metad, rec.tblmd.parent)
                    got[rec.tblmd.name].append(myrec)
        for k in got:
            got[k] = list( unique_justseen( sorted( got[k], key=lambda x: x[0][0] ) ) )
        self.assertEqual(expect, got)
        # test for a file with a single record; check all Record fields
        fn_d = Path(__file__).parent/'toa5'/'TestLogger_Hourly_D.dat'
        with open(fn_d, encoding='ASCII', newline='') as fh2:
            count = 0
            for rec2 in read_toa5_records(fh2, metadatas=metad, filenames=fn_d):
                count += 1
                self.assertEqual(("2021-06-18 23:00:00","12","13.36","25.62","27.14","23.64",None,"63.28",None), rec2.row)
                self.assertEqual(metad.tables['Hourly'], rec2.tblmd)
                # noinspection PyUnresolvedReferences
                self.assertEqual(exp_metadata[1]["envline"], rec2.ctx.envline)
                self.assertEqual(exp_metadata[1]["variant"], rec2.variant)
                self.assertEqual(fn_d, rec2.filenames)
                self.assertEqual(5, rec2.srcline)
                self.assertEqual(DataFileType.TOA5, rec2.filetype)
            self.assertEqual(1, count)

    def test_read_toa5_errors(self):
        md = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        dummyhdr = (
            '"TOA5","Foo","","","","","","foo"',
            '"TIMESTAMP"',
            '"TS"',
            '""',
        )
        with self.assertRaises(RecordError):
            list(read_toa5_records(dummyhdr+('"x","y"',), metadatas=md, filenames="dummy"))
        with self.assertRaises(RecordError):
            list(read_toa5_records(dummyhdr+('"x',), metadatas=md, filenames="dummy"))

    def test_header_match(self):
        bmd = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        env = EnvironmentLine("Foo","","","","","","foo")
        tbl0, var0 = header_match(env, (ColumnHeader("TIMESTAMP","TS"),), (bmd,))
        self.assertEqual(tbl0, bmd.tables['foo'])
        self.assertEqual(var0, next(iter(bmd.tables['foo'].variants.values())))
        # now test all the error cases
        with tempcopy(bmd) as md:
            md.logger_type = -1
            with self.assertRaises(NoMetadataMatch):
                header_match(env, (ColumnHeader("TIMESTAMP","TS"),), (md,))
        with tempcopy(bmd) as md:
            with self.assertRaises(NoMetadataMatch):
                header_match(env._replace(station_name="Bar"), (ColumnHeader("TIMESTAMP","TS"),), (md,))
        with self.assertRaises(RuntimeError):
            header_match(env, (ColumnHeader("TIMESTAMP","TS"),), (bmd,bmd))
        with self.assertRaises(NoVariantMatch):
            header_match(env, (ColumnHeader("Foobar"),), (bmd,))
        with tempcopy(bmd) as md:
            md.tables['foo'].variants = { (ColumnHeader("Foobar"),) : (0,) }
            with self.assertRaises(NoVariantMatch):
                header_match(env, (ColumnHeader("TIMESTAMP","TS"),), (md,))
        with tempcopy(bmd) as md:
            md.tables['foo'].variants[(ColumnHeader("TIMESTAMP","TS"),)] = (0,1)
            with self.assertRaises(RuntimeError):
                header_match(env, (ColumnHeader("TIMESTAMP","TS"),), (md,))

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
