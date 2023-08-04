#!python3
"""General-purpose logger data importer functions.

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
import io
import typing
from igbpyutils.file import AnyPaths, to_Paths, BinaryStream
from more_itertools import peekable
from loggerdata.metadata import Metadata, MdTable, MdCollection
from loggerdata.importdefs import DataFileType, NoTableMatch, Record
from pathlib import Path, PurePath
import warnings
from loggerdata.toa5.dataimport import read_toa5_records
from collections.abc import Generator, Iterable, Sequence

def decide_filetype(fn :PurePath, fh :peekable) -> DataFileType:
    """This function attempts to detect the type of an input file by its name and peeking at the first line."""
    if fn.suffix.lower() == '.dat':
        firstline = fh.peek()
        if firstline.startswith('"TOA5",') or firstline.startswith("TOA5,"):
            return DataFileType.TOA5
        else:
            warnings.warn(f"file with .dat ending was not TOA5")
            return DataFileType.UNKNOWN
    elif fn.suffix.lower() == '.csv':
        return DataFileType.CSV
    else:
        return DataFileType.UNKNOWN

def simple_file_source(paths :AnyPaths) -> Generator[ tuple[tuple[Path], typing.IO[bytes]] ]:
    """A simple file source for :func:`get_record_sources` and :func:`read_records`."""
    for pth in to_Paths(paths):
        with pth.open('rb') as fh:
            yield (pth,), fh

def get_record_sources(*, filesource :Iterable[tuple[ Sequence[PurePath], BinaryStream ]],
                       metadatas :MdCollection|Metadata|MdTable) -> Generator[Generator[Record, None, None], None, None]:
    """This generator turns a set of input files into a set of sources of :class:`Record`s.

    ``source`` can be :func:`simple_file_source`, or it can come from e.g. :mod:`unzipwalk`
    (note that the latter returns tuples of three values, while this function expects two).

    Note that especially the first call of each returned generator may throw exceptions,
    see e.g. :func:`~loggerdata.toa5.dataimport.header_match`.
    """
    metadatas = MdCollection(metadatas)
    for fns, bfh in filesource:
        with io.TextIOWrapper(bfh, 'ASCII', newline='') as fh:
            fh = peekable(fh)
            ft = decide_filetype(fns[-1], fh)
            if ft == DataFileType.TOA5:
                yield read_toa5_records(fh, metadatas=metadatas, filenames=fns)
            elif ft == DataFileType.CSV:
                raise NotImplementedError(f"can't handle CSV yet ({fns!r})")
            else:
                assert ft == DataFileType.UNKNOWN
                warnings.warn(f"skipping unknown file {fns!r}")

def read_records(*, source :Iterable[tuple[ Sequence[PurePath], BinaryStream ]],
                 metadatas :MdCollection|Metadata|MdTable, ignore_notablematch :bool = True) -> Generator[Record, None, None]:
    """This generator reads a set of input files and returns (typechecked) ``Record``s.

    ``source`` can come from ``simple_file_source``, or it can come from e.g. ``unzipwalk``
    (note that ``unzipwalk`` returns a tuple of three values, while this function expects two).
    """
    #TODO: This is hardly used, can it be deprecated in favor of get_record_sources?
    # Or rather: We probably shouldn't typecheck here, and instead just make this a thin wrapper for get_record_sources
    # that also applies the same NoTableMatch "skip tables" logic as datacheck.py
    # (note ignore_notablematch is currently completely unused)
    for recsrc in get_record_sources(filesource=source, metadatas=metadatas):
        recsrc = peekable(recsrc)
        try: recsrc.peek()
        except NoTableMatch:
            if not ignore_notablematch: raise
        for rec in recsrc:
            yield rec.typecheck()
