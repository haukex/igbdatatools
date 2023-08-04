#!/usr/bin/env python3
"""Functions for importing TOA5 data files.

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
import dataclasses
from typing import Optional
from collections.abc import Iterable, Generator, Sequence
from igbpyutils.file import Filename
from loggerdata import toa5
from loggerdata.metadata import Metadata, MdTable, MdCollection, LoggerType, ColumnHeader
from loggerdata.importdefs import NoTableMatch, NoVariantMatch, NoMetadataMatch, Toa5Record, RecordError, DataFileType

def header_match(envline :toa5.EnvironmentLine, columns :tuple[ColumnHeader, ...],
                 metadatas: Iterable[Metadata]) -> tuple[MdTable, tuple[int, ...]]:
    """Figure out which metadata/logger this header belongs to.

    :exc:`NoMetadataMatch`
    :exc:`NoTableMatch`
    :exc:`NoVariantMatch`
    """
    found = []
    for md in metadatas:
        if md.logger_type == LoggerType.TOA5:
            matches = True
            for k, v in dataclasses.asdict(md.toa5_env_match).items():
                if v is not None and getattr(envline,k) != v: matches = False
        else: matches = False
        if matches: found.append(md)
    if len(found)<1:
        raise NoMetadataMatch(repr(envline))
    elif len(found)>1:
        raise RuntimeError(f"header matches multiple metadatas: {envline!r} matches {found!r}")
    else:
        assert len(found)==1
        md = found[0]
        if envline.table_name not in md.tables:
            raise NoTableMatch(repr(envline), table_name=envline.table_name)
        tblmd = md.tables[envline.table_name]
        # identify variant (see metadata.py for info on variant map)
        if columns not in tblmd.variants:
            raise NoVariantMatch(f"header doesn't match any variants: {columns!r}; available are; {list(tblmd.variants.keys())}")
        variant = tblmd.variants[columns]
        if len(variant) != len(columns):
            raise RuntimeError("internal error: variant length incorrect")  # this would indicate a coding mistake in load_logger_metadata
        return tblmd, variant

def read_toa5_records(fh :Iterable[str], *, metadatas :MdCollection|Metadata|MdTable,
        filenames :Optional[Filename|Sequence[Filename]] = None ) -> Generator[Toa5Record, None, None]:
    """Read a TOA5 file, returning a :class:`Toa5Record` for each row in the file.

    :exc:`RecordError` is raised for problems in reading the file.
    """
    metadatas = MdCollection(metadatas)
    csvrd = csv.reader(fh, strict=True)
    envline, columns = toa5.read_header(csvrd)
    tblmd, variant = header_match(envline, columns, metadatas)
    try:
        for origrow in csvrd:
            if len(origrow) != len(variant):
                raise RecordError(f"row column count mismatch, {filenames} line {csvrd.line_num}")
            yield Toa5Record(origrow=tuple(origrow), tblmd=tblmd, variant=variant, envline=envline,
                             filenames=filenames, srcline=csvrd.line_num, filetype=DataFileType.TOA5)
    except csv.Error as ex:
        raise RecordError(f"CSV parse error, {filenames} line {csvrd.line_num}") from ex
    except RecordError: raise
    except Exception as ex:  # pragma: no cover
        raise RecordError(f"error ({filenames} CSV line {csvrd.line_num})") from ex
