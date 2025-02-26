#!/usr/bin/env python
"""Data type library with type checks and type inferral.

These types are based on and are compatible with Postgres data types, but are
more restrictive than the corresponding Postgres types. Only ``str``ings are
accepted, converting other types or checking for ``None`` and ``NaN`` (the
Python value, not the string ``"NaN"``) is left to the user. ``"NaN"``
strings are generally accepted case-insensitively.

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
import re
from collections.abc import Iterable
from typing import Any, Optional
from types import NoneType
from datetime import datetime, timezone, tzinfo
from decimal import Decimal
import numpy

PythonDataTypes = int|Decimal|datetime|NoneType
NumPyDataTypes = numpy.uint32|numpy.int64|numpy.float64|numpy.datetime64|type(numpy.nan)

class BaseType:
    """Abstract base class for data types implemented by this class."""
    pg_type :Optional[str] = None
    np_type :Any = None
    #TODO: Sqlite data type? https://www.sqlite.org/datatype3.html => INTEGER, REAL (8-byte IEEE FP), TEXT (datetime is TEXT=ISO8601 or INTEGER=Unix)
    def check(self, value :str) -> bool:
        """Validate whether the given value is of this type."""
        raise NotImplementedError()  # pragma: no cover
    def to_py(self, value :str) -> PythonDataTypes:
        """Convert a string to a Python object with a type corresponding to the input."""
        raise NotImplementedError()  # pragma: no cover
    def to_np(self, value :str) -> NumPyDataTypes:
        """Convert a string to a NumPy object with a type corresponding to the input."""
        raise NotImplementedError()  # pragma: no cover
    def __eq__(self, other):
        return type(self) == type(other)
    def __repr__(self):
        return type(self).__name__

_parseNum_regex = re.compile(r'''\A Num (?:\( (\d+)(?:,(\d+))? \))? \Z''', re.X)
def from_string(s :str) -> BaseType:
    """Parse a string and instantiate the corresponding data type."""
    if s == "NonNegInt": return NonNegInt()
    elif s == "BigInt": return BigInt()
    elif s == "TimestampNoTz": return TimestampNoTz()
    elif s == "TimestampWithTz": return TimestampWithTz()
    elif s == "OnlyNan": return OnlyNan()
    elif s == "Ignore": return Ignore()
    elif m := _parseNum_regex.fullmatch(s):
        return Num(
            int(m.group(1)) if m.group(1) is not None else None,
            int(m.group(2)) if m.group(2) is not None else None )
    else: raise ValueError(f"failed to parse type {s!r}")

class Num(BaseType):
    """Specifies a numeric data type with a maximum precision and scale.

    This is a subset of the Postgres NUMERIC data type. The following description is adapted from the Postgres
    documentation (https://www.postgresql.org/docs/13/datatype-numeric.html#DATATYPE-NUMERIC-DECIMAL):

    "The *"precision"* of a numeric is the total count of significant digits in the whole number,
    that is, the number of digits to both sides of the decimal point. The *"scale"* of a numeric
    is the count of decimal digits in the fractional part, to the right of the decimal point.
    So the number 23.5141 has a precision of 6 and a scale of 4. Integers can be considered
    to have a scale of zero.

    - ``Num(precision,scale)`` - The precision must be greater than zero; the scale zero or positive, but less than or equal to the precision.
    - ``Num(precision)`` - Selects a scale of 0.
    - ``Num()`` - Numeric values of any precision and scale can be stored, up to the implementation limit on precision
      (up to 131072 digits before the decimal point; up to 16383 digits after the decimal point).
      *Note:* For best compatibility, I don't recommend this option.

    The maximum allowed precision when explicitly specified in the type declaration is 1000."

    However, unlike the Postgres implementation, there is no rounding, and we only allow
    a *maximum* of ``scale`` digits after the decimal point.

    *Note* that the NumPy type returned from this object is ``float64``, which is subject
    to the usual floating point inaccuracies!
    """
    np_type = numpy.float64
    _base_num_regex = re.compile(r'''\A(?!-?\.?\Z)-?\d*(?:\.\d*)?\Z''')
    def __init__(self, precision :Optional[int]=None, scale :Optional[int]=None):
        if precision is None:
            self.pg_type = "NUMERIC"
            if scale is not None: raise TypeError("must specify precision when scale is specified")
            self._num_regex = self._base_num_regex
            self.precision = None
            self.scale = None
        else:
            self.pg_type = f"NUMERIC({precision}" + (f",{scale}" if scale is not None else "") + ")"
            self.precision = precision
            self.scale = scale
            if scale is None: scale = 0
            if not 1 <= precision <= 1000: raise ValueError("precision must be 1 <= N <= 1000")
            if not 0 <= scale <= precision: raise ValueError("scale must be 0 <= N <= precision")
            self._num_regex = re.compile(
                r'\A(?!-?\.?\Z)-?'
                + ( (r'\d{0,' + str(precision-scale) + r'}') if precision-scale else r'0*' )
                + r'(?:\.'
                + ( (r'\d{0,' + str(scale) + r'}') if scale else r'0*' )
                + r')?\Z' )
    def check(self, value :str) -> bool:
        if not isinstance(value, str): return False
        if value.lower() == 'nan': return True
        return bool(self._num_regex.fullmatch(value))
    def to_py(self, value :str) -> Decimal:
        if not self.check(value): raise TypeError()
        return Decimal(value)
    def to_np(self, value :str) -> numpy.float64:
        if not self.check(value): raise TypeError()
        return numpy.float64(value)
    def __eq__(self, other):
        return isinstance(other, Num) and other.precision == self.precision and other.scale == self.scale
    def __lt__(self, other):  # are we less than the other?
        if not isinstance(other, Num): return NotImplemented
        return self.precision < other.precision and self.scale < other.scale
    def __le__(self, other):  # are we less than or equal to the other?
        if not isinstance(other, Num): return NotImplemented
        return self.precision <= other.precision and self.scale <= other.scale
    def __gt__(self, other):  # are we greater than the other?
        if not isinstance(other, Num): return NotImplemented
        return self.precision > other.precision and self.scale > other.scale
    def __ge__(self, other):  # are we greated or equal than the other?
        if not isinstance(other, Num): return NotImplemented
        return self.precision >= other.precision and self.scale >= other.scale
    def __repr__(self):
        if self.precision is None and self.scale is None: return 'Num'
        elif self.scale is None: return f"Num({self.precision})"
        else: return f"Num({self.precision},{self.scale})"

class NonNegInt(BaseType):
    """This data type accepts a non-negative 31-bit integer (and NaN).

    It is therefore compatible with the positive subset of the Postgres 4-byte INTEGER type.
    """
    _uint_regex = re.compile(r'''\A(?!0[0-9])[0-9]+\Z''')
    pg_type = "INTEGER"
    np_type = numpy.uint32
    def check(self, value :str) -> bool:
        if not isinstance(value, str): return False
        if value.lower() == 'nan': return True
        if self._uint_regex.fullmatch(value) is None: return False
        return 0 <= int(value) < 2**31
    def to_py(self, value :str) -> int|None:
        if not self.check(value): raise TypeError()
        if value.lower() == 'nan': return None
        return int(value)
    def to_np(self, value :str) -> numpy.uint32|type(numpy.nan):
        if not self.check(value): raise TypeError()
        if value.lower() == 'nan': return numpy.nan
        return numpy.uint32(value)

class BigInt(BaseType):
    """This data type accepts a 64-bit signed integer (and NaN)."""
    _int_regex = re.compile(r'''\A-?(?!0[0-9])[0-9]+\Z''')
    pg_type = "BIGINT"
    np_type = numpy.int64
    def check(self, value :str) -> bool:
        if not isinstance(value, str): return False
        if value.lower() == 'nan': return True
        if self._int_regex.fullmatch(value) is None: return False
        return -2**63 <= int(value) < 2**63  # note Python 3 ints have unlimited precision
    def to_py(self, value :str) -> int|None:
        if not self.check(value): raise TypeError()
        if value.lower() == 'nan': return None
        return int(value)
    def to_np(self, value :str) -> numpy.int64|type(numpy.nan):
        if not self.check(value): raise TypeError()
        if value.lower() == 'nan': return numpy.nan
        return numpy.int64(value)

class TimestampNoTz(BaseType):
    """This data type excepts a timestamp similar to ISO8601, without a time zone specifier.

    Note that it only accepts a space as the separator between date and time, where ISO8601 requires a ``T``,
    otherwise it is compatible with a subset of ISO8601.

    *Warning:* The NumPy type ``datetime64`` does *not* store time zone information. Timestamps should
    be converted to a known time zone such as UTC, as is done by ``to_np_tz``.
    """
    _timestamp_regex = re.compile(r'''\A\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\Z''')
    pg_type = "TIMESTAMP"
    np_type = numpy.datetime64
    def check(self, value :str) -> bool:
        return bool(self._timestamp_regex.fullmatch(value))
    def to_py(self, value :str) -> datetime:
        """Convert a string to a ``datetime`` object.

        *Warning:* No timezone information is taken into account! Use ``to_py_tz`` instead.
        """
        if not self.check(value): raise TypeError()
        return datetime.fromisoformat(value)
    def to_np(self, value :str) -> numpy.datetime64:
        """Convert a string to a NumPy ``datetime64`` value.

        *Warning:* No timezone information is taken into account! Use ``to_np_tz`` instead.
        """
        if not self.check(value): raise TypeError()
        return numpy.datetime64(value)
    def to_py_tz(self, value :str, tz :tzinfo) -> datetime:
        """Convert a string to a ``datetime`` object, with timezone information."""
        return self.to_py(value).replace(tzinfo=tz)
    def to_np_tz(self, value :str, tz :tzinfo) -> numpy.datetime64:
        """Convert a string to a NumPy ``datetime64`` value in UTC, converted using the timezone information.

        *Note* that the NumPy type ``datetime64`` does *not* store time zone information.
        """
        if not self.check(value): raise TypeError()
        return numpy.datetime64( datetime.fromisoformat(value).replace(tzinfo=tz)
                                 .astimezone(timezone.utc).replace(tzinfo=None).isoformat() )

class TimestampWithTz(BaseType):
    """This data type excepts a timestamp similar to ISO8601, with a time zone specifier.

    Note that it only accepts a space as the separator between date and time, where ISO8601 requires a ``T``,
    otherwise it is compatible with a subset of ISO8601.

    Though many libraries and systems (like Posgres) allow for the time zone specifier with only hours,
    not minutes, SQLite3 functions do require the minutes, so for maximum compatibility we require it too.

    *Warning:* The NumPy type ``datetime64`` does *not* store time zone information.
    Timestamps should be converted to a known time zone such as UTC, as is done by the ``to_np`` function.
    """
    _timestamptz_regex = re.compile(r'''\A\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?: ?[-+]\d\d:\d\d|Z)\Z''')
    pg_type = "TIMESTAMP WITH TIME ZONE"
    np_type = numpy.datetime64
    def check(self, value :str) -> bool:
        return bool(self._timestamptz_regex.fullmatch(value))
    def to_py(self, value :str) -> datetime:
        """Convert a string to ``datetime`` object."""
        if not self.check(value): raise TypeError()
        return datetime.fromisoformat(value)
    def to_np(self, value :str) -> numpy.datetime64:
        """Convert a string to a NumPy ``datetime64`` value in UTC.

        *Note* that the NumPy type ``datetime64`` does *not* store time zone information.
        """
        if not self.check(value): raise TypeError()
        return numpy.datetime64( datetime.fromisoformat(value)
                                 .astimezone(timezone.utc).replace(tzinfo=None).isoformat() )

class OnlyNan(BaseType):
    """This data type only accepts ``NaN``.

    It is intended primarily as a return value from ``TypeInferrer``.
    """
    def check(self, value :str) -> bool:
        return isinstance(value, str) and value.lower() == 'nan'
    def to_py(self, value :str) -> None:
        if not self.check(value): raise TypeError()
        return None
    def to_np(self, value :str) -> type(numpy.nan):
        if not self.check(value): raise TypeError()
        return numpy.nan

class Ignore(BaseType):
    """This data type is a placeholder for columns that don't need to be type checked because their data is never used."""
    def check(self, value :Any) -> True:
        """Always returns ``True``."""
        return True

class TypeInferrer:
    """This class provides a way to analyze multiple values and return the best matching data type.

    The way to use this class is to create a new instance, then call ``send`` repeatedly with
    the values you would like to analyze, and then call ``finish`` to get the inferred data type.
    Or, you can use ``run``, which will call ``send`` on the items of the iterable you give it,
    and then call ``finish`` for you. ``send`` will raise a ``TypeError`` if the type cannot
    be inferred, unless you set ``do_raise`` to ``False``, in which case ``finish`` (or ``run``)
    will return ``None`` instead.
    """
    def __init__(self, *, do_raise :bool=True):
        self.do_raise = do_raise
        # state:
        self.failed = False
        self._is_num = True
        self._num_prec = -1
        self._num_scale = -1
        self._nonnegint :Optional[NonNegInt] = NonNegInt()
        self._bigint :Optional[BigInt] = BigInt()
        self._timestamp :Optional[TimestampNoTz] = TimestampNoTz()
        self._timestamptz :Optional[TimestampWithTz] = TimestampWithTz()
        self._onlynan :Optional[OnlyNan] = OnlyNan()
    def run(self, strings :Iterable[str]):
        for s in strings: self.send(s)
        return self.finish()
    def send(self, string :str) -> None:
        if self.failed: return
        if self._nonnegint and not self._nonnegint.check(string): self._nonnegint = None
        if self._bigint and not self._bigint.check(string): self._bigint = None
        if self._onlynan and not self._onlynan.check(string): self._onlynan = None
        if self._timestamp and not self._timestamp.check(string): self._timestamp = None
        if self._timestamptz and not self._timestamptz.check(string): self._timestamptz = None
        if self._is_num:
            # noinspection PyProtectedMember
            if string.lower()!='nan' and not Num._base_num_regex.fullmatch(string):
                self._is_num = False
            else:
                self._num_prec = max(self._num_prec, sum(c.isdigit() for c in string) )
                if ( dot := string.find('.') ) > -1:
                    self._num_scale = max(self._num_scale, sum(c.isdigit() for c in string[dot:]) )
        if not any((self._is_num, self._nonnegint, self._bigint, self._timestamp, self._timestamptz, self._onlynan)):
            self.failed = True
            if self.do_raise: raise TypeError("failed to infer type")
    def finish(self) -> BaseType:
        if self.failed:
            assert not self.do_raise
            # noinspection PyTypeChecker
            return None
        if self._onlynan:
            assert not self._timestamp and not self._timestamptz and self._nonnegint and self._bigint
            assert self._is_num and self._num_prec == 0 and self._num_scale == -1
            return OnlyNan()
        if self._nonnegint:
            assert not self._timestamp and not self._timestamptz and self._bigint
            assert self._is_num and 0 < self._num_prec < 11 and self._num_scale < 1
            return NonNegInt()
        if self._bigint:
            assert not self._timestamp and not self._timestamptz and not self._nonnegint
            assert self._is_num and 0 < self._num_prec < 20 and self._num_scale < 1
            return BigInt()
        if self._timestamp:
            assert not self._timestamptz and not self._nonnegint and not self._is_num and not self._bigint
            return TimestampNoTz()
        if self._timestamptz:
            assert not self._timestamp and not self._nonnegint and not self._is_num and not self._bigint
            return TimestampWithTz()
        if self._is_num:
            assert not self._timestamp and not self._timestamptz and not self._nonnegint and not self._bigint
            assert self._num_prec > 0
            if self._num_scale < 1: return Num(self._num_prec)
            return Num(self._num_prec, self._num_scale)
        # we should never reach this point, because otherwise we'd have raised an error in "send()"
        assert False   # pragma: no cover

if __name__ == '__main__':  # pragma: no cover
    import sys
    import argparse
    import fileinput
    parser = argparse.ArgumentParser(description='Data Type Tool')
    subparsers = parser.add_subparsers(dest='cmd', required=True)
    parser_infer = subparsers.add_parser('infer', help='Infer Data Types')
    parser_check = subparsers.add_parser('check', help='Check Data Types')
    parser_check.add_argument('type', help="type specification")
    parser.add_argument('files', nargs='*', help='files to read; if empty, stdin is used')
    args = parser.parse_args()
    if args.cmd == 'infer':
        if thetype := TypeInferrer(do_raise=False).run( line.strip() for line in fileinput.input(args.files) ):
            print(repr(thetype))
        else:
            print(f"FAIL: I was not able to infer a type", file=sys.stderr)
            sys.exit(1)
    elif args.cmd == 'check':
        thetype = from_string(args.type)
        for line in fileinput.input(args.files):
            if not thetype.check(line.strip()):
                print(f"FAIL: {line.strip()!r} is not a {thetype}", file=sys.stderr)
                sys.exit(1)
    else: raise RuntimeError(repr(args))
    sys.exit(0)
