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
import os
from enum import Enum
from typing import NamedTuple, Collection
from loggerdata.metadata import MdTable
from loggerdata import toa5
from dataclasses import dataclass

class DataImportError(RuntimeError): pass
class NoMetadataMatch(DataImportError): pass
class NoTableMatch(DataImportError): pass
class NoVariantMatch(DataImportError): pass
class RecordError(DataImportError): pass

class DataFileType(Enum):
    UNKNOWN = 0
    CSV = 1
    TOA5 = 2

@dataclass(frozen=True, kw_only=True)
class RecordContext:
    """Logger-specific context for a ``Record``."""
    pass

@dataclass(frozen=True, kw_only=True)
class Toa5Context(RecordContext):
    envline :toa5.EnvironmentLine

class Record(NamedTuple):
    """A named tuple representing a row of logger data along with all of its context."""
    row :tuple[str|None]
    tblmd :MdTable
    variant :tuple
    ctx :RecordContext
    filenames :str|os.PathLike|Collection[str|os.PathLike]|None
    srcline :int
    filetype :DataFileType
    @property
    def source(self):
        if isinstance(self.filenames, str|os.PathLike) or not self.filenames:
            return str(self.filenames)+":"+str(self.srcline)
        elif len(self.filenames)==1:
            return str(next(iter(self.filenames)))+":"+str(self.srcline)
        else:
            return str(self.filenames)+":"+str(self.srcline)
