#!/usr/bin/env python3
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
from collections.abc import Sequence
from typing import Optional
from more_itertools import first
from fileutils import Filename
from loggerdata.metadata import MdTable
from loggerdata import toa5
from dataclasses import dataclass
from functools import cached_property

class DataImportError(RuntimeError): pass
class NoMetadataMatch(DataImportError): pass
class NoTableMatch(DataImportError): pass
class NoVariantMatch(DataImportError): pass
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
    @cached_property
    def fullrow(self) -> tuple[str|None, ...]:
        if len(self.origrow) != len(self.variant):
            raise RecordError("row column count mismatch")
        newrow :list[str|None] = [None] * len(self.tblmd.columns)
        for old_i, new_i in enumerate(self.variant):
            newrow[new_i] = self.origrow[old_i]
        return tuple(newrow)
    @cached_property
    def source(self) -> str:
        if isinstance(self.filenames, Filename) or not self.filenames:
            return str(self.filenames)+":"+str(self.srcline)
        elif len(self.filenames)==1:
            return str(first(self.filenames))+":"+str(self.srcline)
        else:
            return str(self.filenames)+":"+str(self.srcline)

@dataclass(kw_only=True, frozen=True)
class Toa5Record(Record):
    envline :toa5.EnvironmentLine
