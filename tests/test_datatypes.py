#!/usr/bin/env python3
"""Tests for datatypes library.

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
import datatypes
from decimal import Decimal
from datetime import datetime
import numpy

class TestDataTypes(unittest.TestCase):

    def test_datatypes_eq(self):
        self.assertTrue(datatypes.NonNegInt() == datatypes.NonNegInt())
        self.assertTrue(datatypes.BigInt() == datatypes.BigInt())
        self.assertTrue(datatypes.BigInt() != datatypes.Num())
        self.assertTrue(datatypes.NonNegInt() != datatypes.BigInt())
        self.assertTrue(datatypes.NonNegInt() != datatypes.Num())
        self.assertTrue(datatypes.TimestampNoTz() != datatypes.NonNegInt())
        self.assertTrue(datatypes.TimestampNoTz() != datatypes.BigInt())
        self.assertTrue(datatypes.TimestampNoTz() != datatypes.BaseType())
        self.assertTrue(datatypes.TimestampNoTz() != datatypes.Num())
        self.assertTrue(datatypes.TimestampWithTz() != datatypes.NonNegInt())
        self.assertTrue(datatypes.TimestampWithTz() != datatypes.BigInt())
        self.assertTrue(datatypes.TimestampWithTz() != datatypes.BaseType())
        self.assertTrue(datatypes.TimestampWithTz() != datatypes.Num())
        self.assertTrue(datatypes.TimestampWithTz() != datatypes.TimestampNoTz())
        self.assertTrue(datatypes.TimestampWithTz() == datatypes.TimestampWithTz())
        self.assertTrue(datatypes.TimestampNoTz() == datatypes.TimestampNoTz())
        self.assertTrue(datatypes.OnlyNan() == datatypes.OnlyNan())
        self.assertTrue(datatypes.OnlyNan() != datatypes.NonNegInt())
        self.assertTrue(datatypes.OnlyNan() != datatypes.BigInt())
        self.assertTrue(datatypes.OnlyNan() != datatypes.Num())
        self.assertTrue(datatypes.Num() == datatypes.Num())
        self.assertTrue(datatypes.Num(3) == datatypes.Num(3))
        self.assertTrue(datatypes.Num(5,3) == datatypes.Num(5, 3))
        self.assertTrue(datatypes.Num(5, 3) != datatypes.Num(5, 4))
        self.assertTrue(datatypes.Num(5, 3) != datatypes.Num(5))
        self.assertTrue(datatypes.Num(5,3) != datatypes.Num())
        self.assertTrue(datatypes.Num(5) != datatypes.Num())

    def test_datatypes_str(self):
        self.assertEqual(str(datatypes.TimestampWithTz()), 'TimestampWithTz')
        self.assertEqual(str(datatypes.TimestampNoTz()), 'TimestampNoTz')
        self.assertEqual(str(datatypes.NonNegInt()), 'NonNegInt')
        self.assertEqual(str(datatypes.BigInt()), 'BigInt')
        self.assertEqual(str(datatypes.OnlyNan()), 'OnlyNan')
        self.assertEqual(str(datatypes.Num(10, 8)), 'Num(10,8)')
        self.assertEqual(str(datatypes.Num(3, 3)), 'Num(3,3)')
        self.assertEqual(str(datatypes.Num(4, 0)), 'Num(4,0)')
        self.assertEqual(str(datatypes.Num(7)), 'Num(7)')
        self.assertEqual(str(datatypes.Num()), 'Num')

    def test_datatypes_fromstring(self):
        self.assertIsInstance(datatypes.from_string("NonNegInt"), datatypes.NonNegInt)
        self.assertIsInstance(datatypes.from_string("BigInt"), datatypes.BigInt)
        self.assertIsInstance(datatypes.from_string("TimestampNoTz"), datatypes.TimestampNoTz)
        self.assertIsInstance(datatypes.from_string("TimestampWithTz"), datatypes.TimestampWithTz)
        self.assertIsInstance(datatypes.from_string("OnlyNan"), datatypes.OnlyNan)
        num1 = datatypes.from_string("Num(10,8)")
        self.assertIsInstance(num1, datatypes.Num)
        self.assertEqual( num1.precision, 10 )
        self.assertEqual( num1.scale, 8 )
        num2 = datatypes.from_string("Num")
        self.assertIsInstance(num2, datatypes.Num)
        self.assertEqual( num2.precision, None )
        self.assertEqual( num2.scale, None )
        num3 = datatypes.from_string("Num(7)")
        self.assertIsInstance(num3, datatypes.Num)
        self.assertEqual( num3.precision, 7 )
        self.assertEqual( num3.scale, None )
        num4 = datatypes.from_string("Num(3,3)")
        self.assertIsInstance(num4, datatypes.Num)
        self.assertEqual( num4.precision, 3 )
        self.assertEqual( num4.scale, 3 )
        with self.assertRaises(ValueError): datatypes.from_string("Num()")
        with self.assertRaises(ValueError): datatypes.from_string("Num( 1, 5 )")
        with self.assertRaises(ValueError): datatypes.from_string("Num(1.1,5)")
        with self.assertRaises(ValueError): datatypes.from_string("Num(3,)")
        with self.assertRaises(ValueError): datatypes.from_string("Num(3,2,)")

    def test_datatypes_nonnegint(self):
        uut = datatypes.NonNegInt()
        good = ("0", "1", "2147483646", "2147483647", "NaN", "NAN", "nan")
        bad = (-3000000000, -2147483649, -2147483648, -2147483647, 0, 1, 2147483646,
            2147483647, -1, 1.1, float(1), 'x', '', 2147483648, 3000000000,
            "-2147483648", "-2147483647", "-1", "1.1", "2147483648", "01", "001", "-NaN", "nana")
        for t in good: self.assertTrue( uut.check(t), f"accept {t!r}" )
        for t in bad: self.assertFalse( uut.check(t), f"reject {t!r}" )
        self.assertEqual( uut.pg_type, "INTEGER" )
        self.assertEqual( uut.np_type, numpy.uint32 )
        # conversions
        for t in good:
            if t.lower() != "nan":
                self.assertEqual( uut.to_py(t), int(t) )
                self.assertEqual( uut.to_np(t), numpy.uint32(t) )
        self.assertIsInstance( uut.to_py("123"), int )
        self.assertIsInstance( uut.to_np("123"), numpy.uint32 )
        self.assertIsNone( uut.to_py("NaN") )
        self.assertTrue( numpy.isnan( uut.to_np("Nan") ) )
        with self.assertRaises(TypeError): uut.to_py(bad[-1])
        with self.assertRaises(TypeError): uut.to_np(bad[-1])

    def test_datatypes_bigint(self):
        uut = datatypes.BigInt()
        good = ("0", "1", "-1", "-42", "2147483646", "2147483647", "2147483648", "-2147483648", "NaN", "NAN", "nan",
                "9223372036854775807", "1234567890123456789", "-9223372036854775808", "-1234567890123456789")
        bad = (1.1, float(1), 'x', '', "1.1", "01", "001", "-NaN", "nana", "9223372036854775808", "-9223372036854775809")
        for t in good: self.assertTrue( uut.check(t), f"accept {t!r}" )
        for t in bad: self.assertFalse( uut.check(t), f"reject {t!r}" )
        self.assertEqual( uut.pg_type, "BIGINT" )
        self.assertEqual( uut.np_type, numpy.int64 )
        # conversions
        for t in good:
            if t.lower() != "nan":
                self.assertEqual( uut.to_py(t), int(t) )
                self.assertEqual( uut.to_np(t), numpy.int64(t) )
        self.assertIsInstance( uut.to_py("-42"), int )
        self.assertIsInstance( uut.to_np("-42"), numpy.int64 )
        self.assertIsNone( uut.to_py("NaN") )
        self.assertTrue( numpy.isnan( uut.to_np("Nan") ) )
        with self.assertRaises(TypeError): uut.to_py(bad[-1])
        with self.assertRaises(TypeError): uut.to_np(bad[-1])

    def test_datatypes_timestamp_with_tz(self):
        uut = datatypes.TimestampWithTz()
        good = ('2019-06-12 00:45:00Z', '2019-06-12 01:00:00 +01:00')
        bad = ('2019-06-12 00:30:00', '2019-06-12 00:45:00z',
            ' 2019-06-12 00:30:00 ', '2019-06-12 00:30', '2019-06-12 00:45:00+00',  # these three are allowed by postgres
            '', '19-06-12 00:30:00', '2019-06-12 00', '2019-06-12 00:45:00+0x')
        for t in good: self.assertTrue( uut.check(t), f"accept {t!r}" )
        for t in bad: self.assertFalse( uut.check(t), f"reject {t!r}" )
        self.assertEqual( uut.pg_type, "TIMESTAMP WITH TIME ZONE" )
        self.assertEqual( uut.np_type, numpy.datetime64 )
        # conversions
        self.assertEqual( uut.to_py('2019-06-12 00:45:00Z'), datetime.fromisoformat('2019-06-12T00:45:00+00:00') )
        self.assertEqual( uut.to_np('2019-06-12 00:45:00Z'), numpy.datetime64('2019-06-12T00:45:00') )
        self.assertEqual( uut.to_py('2019-06-12 01:00:00 +01:00'), datetime.fromisoformat('2019-06-12T01:00:00+01:00') )
        self.assertEqual( uut.to_np('2019-06-12 01:00:00 +01:00'), numpy.datetime64('2019-06-12T00:00:00') )
        self.assertIsInstance( uut.to_py("2023-01-02 03:04:05+06:00"), datetime )
        self.assertIsInstance( uut.to_np("2023-01-02 03:04:05+06:00"), numpy.datetime64 )
        with self.assertRaises(TypeError): uut.to_py(bad[0])
        with self.assertRaises(TypeError): uut.to_np(bad[0])

    def test_datatypes_timestamp_no_tz(self):
        uut = datatypes.TimestampNoTz()
        good = ('2019-06-12 00:30:00',)
        bad = ('2019-06-12 00:45:00Z', '2019-06-12 01:00:00 +01:00',
            ' 2019-06-12 00:30:00 ', '2019-06-12 00:30', '2019-06-12 00:45:00+00',  # these three are allowed by postgres
            '', '19-06-12 00:30:00', '2019-06-12 00', '2019-06-12 00:45:00+0x')
        for t in good: self.assertTrue( uut.check(t), f"accept {t!r}" )
        for t in bad: self.assertFalse( uut.check(t), f"reject {t!r}" )
        self.assertEqual( uut.pg_type, "TIMESTAMP" )
        self.assertEqual( uut.np_type, numpy.datetime64 )
        # conversions
        self.assertEqual( uut.to_py('2019-06-12 00:30:00'), datetime.fromisoformat('2019-06-12T00:30:00') )
        self.assertEqual( uut.to_np('2019-06-12 00:30:00'), numpy.datetime64('2019-06-12T00:30:00') )
        self.assertIsInstance( uut.to_py("2023-01-02 03:04:05"), datetime )
        self.assertIsInstance( uut.to_np("2023-01-02 03:04:05"), numpy.datetime64 )
        with self.assertRaises(TypeError): uut.to_py(bad[0])
        with self.assertRaises(TypeError): uut.to_np(bad[0])

    def test_datatypes_num(self):
        uuts = [
            datatypes.Num(),      # Perl: "/\\A(?!-?\\.?\\z)(?:-?\\d{0,}(?:\\.\\d{0,})?|(?i)NaN)\\z/"
            datatypes.Num(10, 5),  # Perl: "/\\A(?!-?\\.?\\z)(?:-?\\d{0,5}(?:\\.\\d{0,5})?|(?i)NaN)\\z/"
            datatypes.Num(7),     # Perl: "/\\A(?!-?\\.?\\z)(?:-?\\d{0,7}(?:\\.0*)?|(?i)NaN)\\z/"
            datatypes.Num(3, 3)    # Perl: "/\\A(?!-?\\.?\\z)(?:-?0*(?:\\.\\d{0,3})?|(?i)NaN)\\z/"
        ]
        #for u in uuts: print(f"uut: {u._num_regex!r}") #Debug
        self.assertEqual( uuts[0].pg_type, "NUMERIC" )
        self.assertEqual( uuts[1].pg_type, "NUMERIC(10,5)" )
        self.assertEqual( uuts[2].pg_type, "NUMERIC(7)" )
        self.assertEqual( uuts[3].pg_type, "NUMERIC(3,3)" )
        self.assertTrue( all( u.np_type==numpy.float64 for u in uuts ) )
        always_pass = ( 'NaN', 'nan', 'NAN',
             '0',  '0.',  '.0',  '0.0',
            '-0', '-0.', '-.0', '-0.0' )
        always_fail = ( '-NaN', '-nan', "nana",
            float("NaN"), 0, 0.0, float(1), 1, 1.1, 0.123, 12345.67890,
            '',  '.',  '1.x',  'x',  'x.',  '.x',  'x.0',  '.0x0',  '0x0',
            '-', '-.', '-1.x', '-x', '-x.', '-.x', '-x.0', '-.0x0', '-0x0' )
        for u in uuts:
            for t in always_pass: self.assertTrue(  u.check(t), f"accept {t!r}" )
            for t in always_fail: self.assertFalse( u.check(t), f"reject {t!r}" )
        # the first element in these tuples is the test case
        # the second element is the list of indicies of the uuts that should pass, the others should fail
        # the comments note which NUMERIC column types corresponding to the uuts Postgres would accept but our regex doesn't
        tests = (
            ('1',            [0,1,2] ),
            ('1.',           [0,1,2] ),
            ('1.0',          [0,1,2] ),
            ('-1',           [0,1,2] ),
            ('-1.',          [0,1,2] ),
            ('-1.0',         [0,1,2] ),
            ('1.1',          [0,1]   ),  # pg accepts 2
            ('0.1',          [0,1,3] ),  # pg accepts 2
            ('.1',           [0,1,3] ),  # pg accepts 2
            ('-1.1',         [0,1]   ),  # untested in pg
            ('-0.1',         [0,1,3] ),  # untested in pg
            ('-.1',          [0,1,3] ),  # untested in pg
            ('12345',        [0,1,2] ),
            ('1234567',      [0,2]   ),
            ('12345678',     [0]     ),
            ('1234567890',   [0]     ),
            ('12345.67890',  [0,1]   ),  # pg accepts 2
            ('-12345.67890', [0,1]   ),  # untested in pg
            ('12345.678901', [0]     ),  # pg accepts 1 and 2
            ('123456.67890', [0]     ),  # pg accepts 2
            ('12345678.90',  [0]     ),
            ('0.123',        [0,1,3] ),  # pg accepts 2
            ('.123',         [0,1,3] ),  # pg accepts 2
            ('0.1234',       [0,1]   ),  # pg accepts 2 and 3
            ('.1234',        [0,1]   ),  # pg accepts 2 and 3
        )
        for t in tests:
            for i, u in enumerate(uuts):
                if i in t[1]:
                    self.assertTrue(  u.check( t[0] ), f"accept {t[0]!r}" )
                    self.assertIsInstance( u.to_py(t[0]), Decimal )
                    self.assertIsInstance( u.to_np(t[0]), numpy.float64 )
                    self.assertEqual( u.to_py(t[0]), Decimal(t[0]) )
                    self.assertEqual( u.to_np(t[0]), numpy.float64(t[0]) )
                else:
                    self.assertFalse( u.check( t[0] ), f"reject {t[0]!r}" )
                    with self.assertRaises(TypeError): u.to_py(t[0])
                    with self.assertRaises(TypeError): u.to_np(t[0])
        with self.assertRaises(TypeError): datatypes.Num(None,3)
        with self.assertRaises(ValueError): datatypes.Num(0)
        with self.assertRaises(ValueError): datatypes.Num(1001)
        with self.assertRaises(ValueError): datatypes.Num(100, -1)
        with self.assertRaises(ValueError): datatypes.Num(100, 101)
        # conversions (in addition to the above)
        for u in uuts:
            self.assertTrue( u.to_py('NaN').is_nan() )
            self.assertTrue( numpy.isnan( u.to_np('NaN') ) )

    def test_datatypes_onlynan(self):
        uut = datatypes.OnlyNan()
        good = ("NaN", "NAN", "nan", "nAN")
        bad = (-5, 5, "5", "-5")
        for t in good: self.assertTrue( uut.check(t), f"accept {t!r}" )
        for t in bad: self.assertFalse( uut.check(t), f"reject {t!r}" )
        # conversions
        self.assertIsNone( uut.to_py("NaN") )
        self.assertTrue( numpy.isnan( uut.to_np("Nan") ) )
        with self.assertRaises(TypeError): uut.to_py(bad[-1])
        with self.assertRaises(TypeError): uut.to_np(bad[-1])

    def test_datatypes_infer(self):
        self.assertEqual(datatypes.TypeInferrer().run(('0', '1', 'NaN', '2', '3')), datatypes.NonNegInt())
        self.assertEqual(datatypes.TypeInferrer().run(('0','1','NaN','2','3','2147483648')), datatypes.BigInt())
        self.assertEqual(datatypes.TypeInferrer().run(('0', '1', 'NaN', '2', '-3')), datatypes.BigInt())
        with self.assertRaises(TypeError): datatypes.TypeInferrer().run(('0', '1', '2', '3', 'abc'))
        self.assertEqual(datatypes.TypeInferrer().run(('2019-06-12 00:30:00', '2021-12-12 15:46:11')), datatypes.TimestampNoTz())
        self.assertEqual(datatypes.TypeInferrer().run(('2019-06-12 00:45:00Z', '2019-06-12 01:00:00 +01:00')), datatypes.TimestampWithTz())
        with self.assertRaises(TypeError): datatypes.TypeInferrer().run(('2019-06-12 00:30:00', '2019-06-12 00:45:00Z'))
        self.assertEqual(datatypes.TypeInferrer().run(('1.0', '3.4', 'NAN')), datatypes.Num(2, 1))
        self.assertEqual(datatypes.TypeInferrer().run(('1.', '23', '-456')), datatypes.Num(3))
        self.assertEqual(datatypes.TypeInferrer().run(('1.2', '1.4', '1.68', '1.123', '12.34')), datatypes.Num(4, 3))
        self.assertEqual(datatypes.TypeInferrer().run(('1.2', '1.68', '1.123', '12.345')), datatypes.Num(5, 3))
        self.assertEqual(datatypes.TypeInferrer().run(('-1.2', '1.68', '12.1', '12345.67')), datatypes.Num(7, 2))
        self.assertEqual(datatypes.TypeInferrer().run(('1234','123','-123456','12345.6')), datatypes.Num(6, 1))
        self.assertEqual(datatypes.TypeInferrer().run(('nan', 'NaN', 'NAN', 'nAN')), datatypes.OnlyNan())
        self.assertEqual(datatypes.TypeInferrer(do_raise=False).run(('abc', '0')), None)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
