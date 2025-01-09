#!/usr/bin/env python
"""Tests for loggerdata.toa5.pandas

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
from loggerdata.toa5.pandas import toa5_to_pandas_dataframe
from loggerdata.toa5 import Toa5Error
from igbpyutils.file import NamedTempFileDeleteLater
import pandas
import pandas.testing

testfile = Path(__file__).parent / 'toa5' / 'TestLogger_Hourly_I.dat'

exp_frame = pandas.DataFrame(
    index = pandas.to_datetime([
        "2021-06-18 11:00:00","2021-06-18 12:00:00","2021-06-18 13:00:00","2021-06-18 14:00:00","2021-06-18 15:00:00","2021-06-18 16:00:00","2021-06-18 17:00:00",
        "2021-06-18 18:00:00","2021-06-18 19:00:00","2021-06-18 20:00:00","2021-06-18 21:00:00","2021-06-18 22:00:00","2021-06-18 23:00:00","2021-06-19 00:00:00",
        "2021-06-19 01:00:00","2021-06-19 02:00:00","2021-06-19 03:00:00","2021-06-19 04:00:00","2021-06-19 05:00:00","2021-06-19 06:00:00","2021-06-19 07:00:00"]),
    data = {
        'RECORD': list(range(21)),
        'BattV_Min[V]':       [13.11,13.09,13.06,13.02,13   ,13   ,12.99,13.01,13.06,13.14,13.23,13.31,13.36,13.42,13.51,13.56,13.59,13.59,13.5 ,13.4 ,13.33],
        'PTemp_C_Min[°C]':    [35.3 ,35.61,36.56,37.42,38.42,38.87,37.97,35.91,33.51,30.82,28.62,27.14,25.62,23.72,22.05,21.66,21.58,21.54,22.41,25.53,28.41],
        'PTemp_C_Max[°C]':    [35.65,36.56,37.42,38.6 ,38.87,39.16,38.96,37.97,35.9 ,33.51,30.82,28.62,27.14,25.61,23.72,22.05,21.79,22.41,25.52,28.4 ,30.83],
        'AirT_C(42)/Smp[°C]': [32.41,32.96,33.47,33.64,33.55,33.66,32.86,31.27,29.74,27.96,26.29,25.14,23.64,21.47,19.67,20.79,21.01,20.83,22.45,24.41,26.35],
        'RelHumid/Smp[%]':    [24.46,24   ,24.35,24.19,24.8 ,23.87,28.37,35.81,40.61,45.66,49.31,54.85,63.28,81   ,100  ,76.63,77.35,77.53,69.93,56.34,50.1 ],
    } )
exp_frame.index.name = 'TIMESTAMP'

# just a copy of the above with csvnames=False
exp_frame_nocsvnames = pandas.DataFrame(
    index = pandas.to_datetime([
        "2021-06-18 11:00:00","2021-06-18 12:00:00","2021-06-18 13:00:00","2021-06-18 14:00:00","2021-06-18 15:00:00","2021-06-18 16:00:00","2021-06-18 17:00:00",
        "2021-06-18 18:00:00","2021-06-18 19:00:00","2021-06-18 20:00:00","2021-06-18 21:00:00","2021-06-18 22:00:00","2021-06-18 23:00:00","2021-06-19 00:00:00",
        "2021-06-19 01:00:00","2021-06-19 02:00:00","2021-06-19 03:00:00","2021-06-19 04:00:00","2021-06-19 05:00:00","2021-06-19 06:00:00","2021-06-19 07:00:00"]),
    data = {
        'RECORD': list(range(21)),
        'BattV_Min':   [13.11,13.09,13.06,13.02,13   ,13   ,12.99,13.01,13.06,13.14,13.23,13.31,13.36,13.42,13.51,13.56,13.59,13.59,13.5 ,13.4 ,13.33],
        'PTemp_C_Min': [35.3 ,35.61,36.56,37.42,38.42,38.87,37.97,35.91,33.51,30.82,28.62,27.14,25.62,23.72,22.05,21.66,21.58,21.54,22.41,25.53,28.41],
        'PTemp_C_Max': [35.65,36.56,37.42,38.6 ,38.87,39.16,38.96,37.97,35.9 ,33.51,30.82,28.62,27.14,25.61,23.72,22.05,21.79,22.41,25.52,28.4 ,30.83],
        'AirT_C(42)':  [32.41,32.96,33.47,33.64,33.55,33.66,32.86,31.27,29.74,27.96,26.29,25.14,23.64,21.47,19.67,20.79,21.01,20.83,22.45,24.41,26.35],
        'RelHumid':    [24.46,24   ,24.35,24.19,24.8 ,23.87,28.37,35.81,40.61,45.66,49.31,54.85,63.28,81   ,100  ,76.63,77.35,77.53,69.93,56.34,50.1 ],
    } )
exp_frame_nocsvnames.index.name = 'TIMESTAMP'

class TestToa5Pandas(unittest.TestCase):

    def test_toa5_pandas(self):
        gotdf = toa5_to_pandas_dataframe(testfile)
        pandas.testing.assert_frame_equal( exp_frame, gotdf )
        self.assertEqual(gotdf.attrs['toa5_envline']._asdict(), { "station_name":"TestLogger", "logger_model":"CR1000X", "logger_serial":"12342",
            "logger_os":"CR1000X.Std.03.02", "program_name":"CPU:TestLogger.CR1X", "program_sig":"2438", "table_name":"Hourly" })
        self.assertEqual(gotdf.attrs['columns'], ( ("TIMESTAMP","TS",""), ("RECORD","RN",""), ("BattV_Min","Volts","Min"),
            ("PTemp_C_Min","Deg C","Min"), ("PTemp_C_Max","Deg C","Max"), ("AirT_C(42)","Deg C","Smp"), ("RelHumid","%","Smp") ))

    # just a copy of the above with csvnames=False
    def test_toa5_pandas_nocsvnames(self):
        gotdf = toa5_to_pandas_dataframe(testfile, csvnames=False)
        pandas.testing.assert_frame_equal( exp_frame_nocsvnames, gotdf )
        # the following lines are identical between the two tests
        self.assertEqual(gotdf.attrs['toa5_envline']._asdict(), { "station_name":"TestLogger", "logger_model":"CR1000X", "logger_serial":"12342",
            "logger_os":"CR1000X.Std.03.02", "program_name":"CPU:TestLogger.CR1X", "program_sig":"2438", "table_name":"Hourly" })
        self.assertEqual(gotdf.attrs['columns'], ( ("TIMESTAMP","TS",""), ("RECORD","RN",""), ("BattV_Min","Volts","Min"),
            ("PTemp_C_Min","Deg C","Min"), ("PTemp_C_Max","Deg C","Max"), ("AirT_C(42)","Deg C","Smp"), ("RelHumid","%","Smp") ))

    def test_toa5_pandas_errors(self):
        with NamedTempFileDeleteLater() as tf:
            tf.write(b'"TOA5","a","b","c","d","e","f","g"\n')
            tf.write(b'"RECORD","BattV_Min"\n')
            tf.write(b'"RN","Volts"\n')
            tf.write(b'"","Min"\n')
            tf.write(b'5,12\n')
            tf.close()
            with self.assertRaises(Toa5Error):
                toa5_to_pandas_dataframe(tf.name)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
