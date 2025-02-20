#!/usr/bin/env python
"""Tests for loggerdata.qualitycheck.

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
from collections.abc import Iterable
import loggerdata.qualitycheck as qc
from loggerdata.metadata import DataInterval
from datetime import datetime

class TestLoggerQualityCheck(unittest.TestCase):

    def test_basic_quality(self):
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality("abc") )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(0) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(2) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(9) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(-42) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(9384745603482650343324123424564563412238) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(float(0.0)) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(float(1.0)) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(float(7998.9999)) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(float(7999.0001)) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(float(-7998.9999)) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(float(-7999.0001)) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality("inf") )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality("Infinity") )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(True) )
        self.assertEqual( qc.BasicQuality.GOOD, qc.basic_quality(datetime.now()) )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality(7999) )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality(-7999) )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality("7999") )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality("-7999") )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality(float(7999.0000)) )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality(float(-7999.0000)) )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality("") )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality("        ") )
        self.assertEqual( qc.BasicQuality.UNUSUAL, qc.basic_quality(complex(1,2)) )
        self.assertEqual( qc.BasicQuality.BAD, qc.basic_quality(float("NaN")) )
        self.assertEqual( qc.BasicQuality.BAD, qc.basic_quality(float("inf")) )
        self.assertEqual( qc.BasicQuality.BAD, qc.basic_quality("NAN") )
        self.assertEqual( qc.BasicQuality.BAD, qc.basic_quality(None) )
        self.assertEqual( qc.BasicQuality.BAD, qc.basic_quality(object()) )

    def test_check_timeseq_strict(self):
        def run(interval: DataInterval, seq :Iterable[tuple[datetime, qc.BasicQuality]], *, floor :bool=False):
            self.assertEqual( tuple( (x[1] for x in seq) ),
               tuple( qc.check_timeseq_strict( ( interval.floor(x[0]) if floor else x[0] for x in seq), interval=interval ) ) )
        self.maxDiff = None
        run( DataInterval.MIN15, (
            (datetime(2022,5,22,12,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,13,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,13,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,13,45,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,22,14,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,14,15, 1), qc.BasicQuality.BAD),
            (datetime(2022,5,22,14,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,14,44,00), qc.BasicQuality.BAD),
            (datetime(2022,5,22,15,00,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,22,15,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,15,14,00), qc.BasicQuality.BAD),
            (datetime(2022,5,22,15,30,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,22,15,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,18,00,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,22,18,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,18,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,13,30,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,24,13,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,00,00), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,17,12), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,46,33), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,48,57), qc.BasicQuality.BAD),
            (datetime(2022,5,24,15,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,15,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,15,40,00), qc.BasicQuality.BAD),
            (datetime(2022,5,24,15,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,16,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,16,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,16,25,00), qc.BasicQuality.BAD),
            (datetime(2022,5,24,16,40,00), qc.BasicQuality.BAD),
            (datetime(2022,5,24,16,42,30), qc.BasicQuality.BAD),
        ) )
        run( DataInterval. MIN15, (
            (datetime(2022,5,22,12,00,16), qc.BasicQuality.BAD),
            (datetime(2022,5,22,12,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,25,00), qc.BasicQuality.BAD),
        ) )
        run( DataInterval.MIN15, (
            (datetime(2022,5,22,12, 7,43), qc.BasicQuality.BAD),
            (datetime(2022,5,22,12,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,29,11), qc.BasicQuality.BAD),
        ) )
        run( DataInterval.MIN15, (
            (datetime(2022,5,22,12,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,13,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,13,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,13,45,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,22,14,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,14,15, 1), qc.BasicQuality.BAD),
            (datetime(2022,5,22,14,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,14,46,00), qc.BasicQuality.BAD),
            (datetime(2022,5,22,15,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,15,29,59), qc.BasicQuality.BAD),
            (datetime(2022,5,22,15,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,15,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,18,00,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,22,18,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,18,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,13,30,00), qc.BasicQuality.UNUSUAL),
            (datetime(2022,5,24,13,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,00,00), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,29,59), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,14,35,11), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,30, 1), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,40,22), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,44,59), qc.BasicQuality.BAD),
            (datetime(2022,5,24,14,45,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,15,14,59), qc.BasicQuality.BAD),
            (datetime(2022,5,24,15,15,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,15,33,33), qc.BasicQuality.BAD),
            (datetime(2022,5,24,15,49, 9), qc.BasicQuality.BAD),
            (datetime(2022,5,24,16,00, 1), qc.BasicQuality.BAD),
            (datetime(2022,5,24,16,16,12), qc.BasicQuality.BAD),
            (datetime(2022,5,24,16,41,53), qc.BasicQuality.BAD),
            (datetime(2022,5,24,16,59,00), qc.BasicQuality.BAD),
            (datetime(2022,5,24,17,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,15,15,00), qc.BasicQuality.BAD),
            (datetime(2022,5,24,15,30,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,24,15,45,00), qc.BasicQuality.GOOD),
        ) )
        run( DataInterval.MIN30, (
            (datetime(2022,5,22,12,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,12,35,43), qc.BasicQuality.BAD),
            (datetime(2022,5,22,12,45,00), qc.BasicQuality.BAD),
            (datetime(2022,5,22,13,00,00), qc.BasicQuality.GOOD),
        ) )
        run( DataInterval.HOUR1, (
            (datetime(2022,5,22,12,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,13,10,00), qc.BasicQuality.BAD),
            (datetime(2022,5,22,14,00,00), qc.BasicQuality.GOOD),
            (datetime(2022,5,22,17, 5,00), qc.BasicQuality.BAD),
        ) )
        run( DataInterval.DAY1, (
            (datetime(2023,1,2,0), qc.BasicQuality.GOOD),
            (datetime(2023,1,3,1,5), qc.BasicQuality.BAD),
            (datetime(2023,1,4,0), qc.BasicQuality.GOOD),
            (datetime(2023,1,5,0), qc.BasicQuality.GOOD),
            (datetime(2023,1,7,23), qc.BasicQuality.BAD),
        ) )
        # Especially weekly and monthly sampling intervals are usually sampling that is performed manually,
        # therefore, to check such time sequences, it makes more sense to floor the time values first.
        run( DataInterval.DAY1, (
            (datetime(2023,3,10, 0, 0, 0), qc.BasicQuality.GOOD),
            (datetime(2023,3,11, 0, 0, 0), qc.BasicQuality.GOOD),
            (datetime(2023,3,12,13,45, 0), qc.BasicQuality.GOOD),
            (datetime(2023,3,13,15,27,33), qc.BasicQuality.GOOD),
            (datetime(2023,3,14, 3,11,55), qc.BasicQuality.GOOD),
            (datetime(2023,3,15,23,59,59), qc.BasicQuality.GOOD),
            (datetime(2023,3,16, 0, 0, 1), qc.BasicQuality.GOOD),
            (datetime(2023,3,18,14,15, 0), qc.BasicQuality.UNUSUAL),
            (datetime(2023,3,19, 5,11,11), qc.BasicQuality.GOOD),
            (datetime(2023,3,19,23,22,22), qc.BasicQuality.BAD),
            (datetime(2023,3,20,12,34,56), qc.BasicQuality.GOOD),
        ), floor=True )
        run( DataInterval.WEEK1, (
            (datetime(2023,3,10, 0, 0, 0), qc.BasicQuality.GOOD),
            (datetime(2023,3,14,11,22,33), qc.BasicQuality.GOOD),
            (datetime(2023,3,26,23,59,59), qc.BasicQuality.GOOD),
            (datetime(2023,3,27,15,55,23), qc.BasicQuality.GOOD),
            (datetime(2023,4, 5, 9, 6, 7), qc.BasicQuality.GOOD),
            (datetime(2023,4,15,10,32,23), qc.BasicQuality.GOOD),
            (datetime(2023,4,16,11,31,13), qc.BasicQuality.BAD),
            (datetime(2023,4,23,23,59,59), qc.BasicQuality.GOOD),
            (datetime(2023,4,24, 0, 0, 0), qc.BasicQuality.GOOD),
            (datetime(2023,4,30,23,59,59), qc.BasicQuality.BAD),
            (datetime(2023,5,16,11,54,12), qc.BasicQuality.UNUSUAL),
            (datetime(2023,5,25,18,12,45), qc.BasicQuality.GOOD),
        ), floor=True )
        run( DataInterval.MONTH1, (
            (datetime(2023,1,10,11, 4,32), qc.BasicQuality.GOOD),
            (datetime(2023,2,22,19,47,11), qc.BasicQuality.GOOD),
            (datetime(2023,3,15,11, 0,44), qc.BasicQuality.GOOD),
            (datetime(2023,4,30,23,59,59), qc.BasicQuality.GOOD),
            (datetime(2023,5, 1, 0, 0, 0), qc.BasicQuality.GOOD),
            (datetime(2023,7,18,10,23,29), qc.BasicQuality.UNUSUAL),
            (datetime(2023,7, 1, 5,23, 2), qc.BasicQuality.BAD),
            (datetime(2023,8,16,18,36,25), qc.BasicQuality.GOOD),
        ), floor=True )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
