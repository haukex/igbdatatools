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
import warnings
from typing import NamedTuple
from igbpyutils.iter import no_duplicates
from loggerdata.metadata import ColumnHeader, MdTable
from collections.abc import Iterator, Sequence, Iterable, Generator

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
    # noinspection PyShadowingNames,PyUnresolvedReferences
    """Read the header of a TOA5 file.

    A common use case to read a TOA5 file would be:

    >>> import csv
    ... from loggerdata.metadata import ColumnHeader
    ... from loggerdata.toa5 import read_header
    ... with open(filename, encoding='ASCII', newline='') as fh:
    ...     csvrd = csv.reader(fh, strict=True)
    ...     envline, columns = read_header(csvrd)
    ...     header = [ ColumnHeader(*col).csv for col in columns ]
    ...     for row in csvrd:
    ...         pass  # do something with each row here
    """
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

def meta2hdr(tblmd :MdTable) -> Generator[tuple[str, ...], None, None]:
    """Create an environment line based on the logger's ``toa5_env_match`` metadata."""
    yield tuple( ("TOA5", *(getattr(tblmd.parent.toa5_env_match, c) for c in EnvironmentLine._fields if c!='table_name'), tblmd.name) )
    yield tuple( '' if c.name is None else c.name for c in tblmd.columns )
    yield tuple( '' if c.unit is None else c.unit for c in tblmd.columns )
    yield tuple( '' if c.prc  is None else c.prc  for c in tblmd.columns )

def envline_merge(envs :Iterable[EnvironmentLine], *, sep :str='|') -> EnvironmentLine:
    """Create an environment line by merging together a set of existing environment lines."""
    thesets :dict[str, set[str]] = { k: set() for k in EnvironmentLine._fields }
    for env in envs:
        for k in EnvironmentLine._fields:
            thesets[k].add( getattr(env, k) )
    if len(thesets['table_name'])>1:
        warnings.warn("Merged more than one table name")
    return EnvironmentLine(**{ k: sep.join( sorted( thesets[k] ) ) for k in EnvironmentLine._fields })
