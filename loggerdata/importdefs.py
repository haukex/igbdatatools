#!/usr/bin/env python
"""Common definitions used in the importing of logger data.

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
from enum import Enum
from collections.abc import Sequence, Generator
from typing import Optional, Self
from more_itertools import first
from dataclasses import dataclass
from functools import cached_property
from igbpyutils.file import Filename
from loggerdata import toa5
from loggerdata.metadata import Metadata, MdTable, MappingType
from datatypes import TimestampNoTz, PythonDataTypes, NumPyDataTypes

#TODO: DataImportError subclasses should probably have even more context, like filenames
# grep -Er 'DataImportError|NoMetadataMatch|NoTableMatch|NoVariantMatch|RecordError|Toa5Error'
class DataImportError(RuntimeError): pass
class NoMetadataMatch(DataImportError): pass
class NoTableMatch(DataImportError):
    def __init__(self, message :str, *, md :Metadata, table_name :str):
        self.message = message
        self.md = md
        self.table_name = table_name
class NoVariantMatch(DataImportError):
    def __init__(self, message :str, *, tblmd :MdTable):
        self.message = message
        self.tblmd = tblmd
class RecordError(DataImportError): pass

class DataFileType(Enum):
    UNKNOWN = 0
    CSV = 1
    TOA5 = 2

@dataclass(kw_only=True, frozen=True)
class Record:
    """A named tuple representing a row of logger data along with all of its context."""
    origrow :tuple[str, ...]
    tblmd :MdTable
    variant :tuple[int, ...]
    filenames :Optional[Filename|Sequence[Filename]]
    srcline :int
    filetype :DataFileType

    def getcolval(self, key):
        """Get the value of a column by the column name."""
        if not isinstance(key, str): raise TypeError("key")
        for i, col in enumerate(self.tblmd.columns):
            if col.name == key:
                return self.fullrow[i]
        raise KeyError(key)

    @cached_property
    def fullrow(self) -> tuple[str|None, ...]:
        """While ``origrow`` represents the columns read from the input file,
        this property represents the columns as are stored in the table metadata."""
        if len(self.origrow) != len(self.variant):
            raise RecordError("row column count mismatch")
        newrow :list[str|None] = [None] * len(self.tblmd.columns)
        for old_i, new_i in enumerate(self.variant):
            newrow[new_i] = self.origrow[old_i]
        return tuple(newrow)

    @cached_property
    def source(self) -> str:
        """A string representing the source filename(s) and line number for this record."""
        if isinstance(self.filenames, Filename) or not self.filenames:
            return str(self.filenames)+":"+str(self.srcline)
        elif len(self.filenames)==1:
            return str(first(self.filenames))+":"+str(self.srcline)
        else:
            return str(self.filenames)+":"+str(self.srcline)

    def typecheck(self) -> Self:
        """Run type checks and raise an error if a column does not match its declared type.

        Returns this object to allow method chaining."""
        for val, vi in zip(self.origrow, self.variant, strict=True):
            col = self.tblmd.columns[vi]
            if col.type:  # To-Do for Later: column types should eventually become mandatory (see metadata for similar note)
                if not col.type.check(val):
                    raise TypeError(f"Column {col.tup}: value {val!r} does not match {col.type}")
        return self

    def fullrow_as_py(self) -> Generator[PythonDataTypes, None, None]:
        """Convert the ``fullrow`` from strings to the corresponding Python types
        (except where column type information is not available)."""
        for val, col in zip(self.fullrow, self.tblmd.columns, strict=True):
            if col.type:  # To-Do for Later: column types should eventually become mandatory (see metadata for similar note)
                if isinstance(col.type, TimestampNoTz):
                    yield col.type.to_py_tz(val, self.tblmd.parent.tz)
                else: yield col.type.to_py(val)
            else: yield val

    def fullrow_as_np(self) -> Generator[NumPyDataTypes, None, None]:
        """Convert the ``fullrow`` from strings to the corresponding NumPy types."""
        if any( not col.type for col in self.tblmd.columns ):  # To-Do for Later: column types should eventually become mandatory (see metadata for similar note)
            raise TypeError(f"Every column in {self.tblmd.name} needs a type so it can be converted")
        for val, col in zip(self.fullrow, self.tblmd.columns, strict=True):
            if isinstance(col.type, TimestampNoTz):
                yield col.type.to_np_tz(val, self.tblmd.parent.tz)
            else: yield col.type.to_np(val)

    def view(self, viewname :str) -> Generator[str|None, None, None]:
        """Generate the requested view of this row."""
        v = self.tblmd.mappings[viewname]
        if v.type != MappingType.VIEW:
            raise TypeError(f"expected a VIEW mapping, not {v.type!r}")
        for i in v.old_idxs:
            yield self.fullrow[i]

@dataclass(kw_only=True, frozen=True)
class Toa5Record(Record):
    envline :toa5.EnvironmentLine
