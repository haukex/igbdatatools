#!python3
"""Functions for handling TOA5 files.

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
import csv
from typing import NamedTuple
from igbitertools import no_duplicates
from loggerdata.metadata import ColumnHeader
from collections.abc import Iterator, Sequence

class Toa5Error(RuntimeError): pass

class EnvironmentLine(NamedTuple):
    """Represents a TOA5 "Environment Line"."""
    station_name :str
    logger_model :str
    logger_serial :str
    logger_os :str
    program_name :str
    program_sig :str
    table_name :str

_envline_keys = ('toa5',) + EnvironmentLine._fields
def read_header(csvreader :Iterator[Sequence[str]]) -> tuple[EnvironmentLine, tuple[ColumnHeader, ...]]:
    """Read the header of a TOA5 file."""
    # ### Read the environment line, for file format see e.g. the CR1000 manual
    try:
        envline = next(csvreader)
    except StopIteration as ex:
        raise Toa5Error("failed to read environment line") from ex
    except csv.Error as ex:
        raise Toa5Error("CSV parse error on environment line") from ex
    if len(envline)<1 or envline[0]!='TOA5': raise Toa5Error("not a TOA5 file?")
    if len(_envline_keys) != len(envline): raise Toa5Error("TOA5 environment line length mismatch")
    envline_dict = dict(zip(_envline_keys, envline, strict=True))
    del envline_dict['toa5']
    # ### Read the header rows
    try:
        field_names = next(csvreader)
        units = next(csvreader)  # "engineering units", "strictly for documentation"
        proc = next(csvreader)  # "data process used to produce the field of data", abbreviated "Prc"
    except StopIteration as ex:
        raise Toa5Error("unexpected end of headers") from ex
    except csv.Error as ex:
        raise Toa5Error("CSV parse error on headers") from ex
    if len(field_names) != len(units) or len(field_names) != len(proc):
        raise Toa5Error("header column count mismatch")
    try: set(no_duplicates(field_names, name='column name'))
    except ValueError as ex: raise Toa5Error(*ex.args)
    columns = tuple( ColumnHeader(*c) for c in zip(field_names, units, proc, strict=True) )
    return EnvironmentLine(**envline_dict), columns
