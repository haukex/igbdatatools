#!/usr/bin/env python3
"""Tests for loggerdata.toa5.

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
import csv
from pathlib import Path
from loggerdata.metadata import ColumnHeader, load_logger_metadata
from loggerdata import toa5

expect_daily_meta2hdr = (
    ("TOA5","TestLogger","CR1000X","12342",None,None,None,"Daily"),
    ("TIMESTAMP","RECORD","BattV_Min","BattV_TMn","PTemp_C_Min","PTemp_C_TMn","PTemp_C_Max","PTemp_C_TMx"),
    ("TS","RN","Volts","","Deg C","","Deg C",""),
    ("","","Min","TMn","Min","TMn","Max","TMx"),
)
expect_hourly_meta2hdr = (
    ("TOA5","TestLogger","CR1000X","12342",None,None,None,"Hourly"),
    ("TIMESTAMP","RECORD","BattV_Min","PTemp_C_Min","PTemp_C_Max","AirT_C(42)","AirT_C_Avg","RelHumid","BP_mbar_Avg"),
    ("TS","RN","Volts","Deg C","Deg C","Deg C","Deg C","%","mbar"),
    ("","","Min","Min","Max","Smp","Avg","Smp","Avg"),
)

class TestToa5(unittest.TestCase):

    def test_toa5(self):
        expenv = toa5.EnvironmentLine(station_name="TestLogger",logger_model="CR1000X",logger_serial="12342",
            logger_os="CR1000X.Std.03.02",program_name="CPU:TestLogger.CR1X",program_sig="2438",table_name="Daily")
        inpath = Path(__file__).parent/'toa5'
        with (inpath/'TestLogger_Daily_1.dat').open(encoding='ASCII', newline='') as fh:
            csvrd = csv.reader(fh, strict=True)
            envline, columns = toa5.read_header(csvrd)
            self.assertEqual(envline, expenv)
            self.assertEqual(columns, (
                ColumnHeader(name="TIMESTAMP",unit="TS"),
                ColumnHeader(name="RECORD",unit="RN"),
                ColumnHeader(name="BattV_Min",unit="Volts",prc="Min"),
                ColumnHeader(name="BattV_TMn",prc="TMn"),
                ColumnHeader(name="PTemp_C_Min",unit="Deg C",prc="Min"),
                ColumnHeader(name="PTemp_C_TMn",prc="TMn"),
                ColumnHeader(name="PTemp_C_Max",unit="Deg C",prc="Max"),
                ColumnHeader(name="PTemp_C_TMx",prc="TMx"),
            ) )
        with (inpath/'TestLogger_Hourly_A.dat').open(encoding='ASCII', newline='') as fh:
            csvrd = csv.reader(fh, strict=True)
            envline, columns = toa5.read_header(csvrd)
            self.assertEqual(envline, expenv._replace(table_name="Hourly"))
            self.assertEqual(columns, (
                ColumnHeader(name="TIMESTAMP",unit="TS"),
                ColumnHeader(name="RECORD",unit="RN"),
                ColumnHeader(name="BattV_Min",unit="Volts",prc="Min"),
                ColumnHeader(name="PTemp_C_Min",unit="Deg C",prc="Min"),
                ColumnHeader(name="PTemp_C_Max",unit="Deg C",prc="Max"),
                ColumnHeader(name="AirT_C(42)",unit="Deg C",prc="Smp"),
                ColumnHeader(name="RelHumid",unit="%",prc="Smp"),
            ) )

    def test_bad_toa5(self):
        inpath = Path(__file__).parent/'bad_toa5'
        for f in ( x for x in inpath.iterdir() if x.is_file() and x.suffix == '.dat' ):
            with open(f, encoding='ASCII', newline='') as fh:
                csvrd = csv.reader(fh, strict=True)
                with self.assertRaises(toa5.Toa5Error):
                    toa5.read_header(csvrd)

    def test_meta2hdr(self):
        md = load_logger_metadata( Path(__file__).parent / 'TestLogger.json' )
        self.assertEqual(expect_daily_meta2hdr, tuple(toa5.meta2hdr(md.tables['Daily'])))
        self.assertEqual(expect_hourly_meta2hdr, tuple(toa5.meta2hdr(md.tables['Hourly'])))

    def test_envline_merge(self):
        envs = (
            toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger.CR1X", program_sig="2438", table_name="Daily" ),
            toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger.CR1X", program_sig="2438", table_name="Hourly"),
            toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger.CR1X", program_sig="1234", table_name="Hourly"),
        )
        exp = toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger.CR1X", program_sig="1234|2438", table_name="Daily|Hourly")
        with self.assertWarns(UserWarning):
            got = toa5.envline_merge(envs)
        self.assertEqual( exp, got )

        envs2 = (
            toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.04", program_name="CPU:TestLogger_v1.CR1X", program_sig="2438", table_name="Hourly" ),
            toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger_v2.CR1X", program_sig="2438", table_name="Hourly"),
            toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02", program_name="CPU:TestLogger_v3.CR1X", program_sig="1234", table_name="Hourly"),
        )
        exp2 = toa5.EnvironmentLine(station_name="TestLogger", logger_model="CR1000X", logger_serial="12342", logger_os="CR1000X.Std.03.02;CR1000X.Std.03.04", program_name="CPU:TestLogger_v1.CR1X;CPU:TestLogger_v2.CR1X;CPU:TestLogger_v3.CR1X", program_sig="1234;2438", table_name="Hourly")
        self.assertEqual( exp2, toa5.envline_merge(envs2, sep=';') )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
