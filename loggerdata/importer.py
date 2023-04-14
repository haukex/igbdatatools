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
from igbpyutils.file import AnyPaths, to_Paths
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
    """A simple file source for ``read_records``."""
    for pth in to_Paths(paths):
        with pth.open('rb') as fh:
            yield (pth,), fh

def read_records(*, source :Iterable[tuple[ Sequence[PurePath], typing.IO[bytes]|io.RawIOBase|io.BufferedIOBase ]],
                 metadatas :MdCollection|Metadata|MdTable, ignore_notablematch :bool = True) -> Generator[Record, None, None]:
    """This generator reads a set of input files and returns ``Record``s.

    ``source`` can come from ``simple_file_source``, or it can come from e.g. ``unzipwalk``
    (note that ``unzipwalk`` returns a tuple of three values, while this function expects two).
    """
    metadatas = MdCollection(metadatas)
    for fns, bfh in source:
        with io.TextIOWrapper(bfh, 'ASCII', newline='') as fh:
            fh = peekable(fh)
            ft = decide_filetype(fns[-1], fh)
            if ft == DataFileType.TOA5:
                datasrc = peekable(read_toa5_records(fh, metadatas=metadatas, filenames=fns))
                try: datasrc.peek()
                except NoTableMatch:
                    if not ignore_notablematch: raise
            elif ft == DataFileType.CSV:
                raise NotImplementedError(f"can't handle CSV yet ({fns!r})")
            elif ft == DataFileType.UNKNOWN:
                warnings.warn(f"skipping unknown file {fns!r}")
                continue
            else: raise RuntimeError("enum not covered completely")  # pragma: no cover
            for rec in datasrc: yield rec.typecheck()
