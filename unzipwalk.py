#!/usr/bin/env python3
"""Library to recursively read compressed files.

Author, Copyright, and License
------------------------------
Copyright (c) 2022 Hauke Daempfling (haukex@zero-g.net)
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
import stat
from enum import Enum
from gzip import GzipFile
from itertools import chain
from pathlib import PurePosixPath, PurePath, Path
from tarfile import TarFile
from zipfile import ZipFile
import typing
from typing import Optional
from collections.abc import Generator, Sequence
from fileutils import AnyPaths, to_Paths

class FileType(Enum):
    FILE = 0
    ARCHIVE = 1
    DIR = 2
    SYMLINK = 3
    OTHER = 4

def _procfile(fns :tuple[PurePath, ...], fh :typing.IO[bytes]|GzipFile) \
        -> Generator[ tuple[ tuple[PurePath, ...], Optional[typing.IO[bytes]], FileType ], None, None ]:
    bfnl = fns[-1].name.lower()
    if bfnl.endswith('.tar.gz') or bfnl.endswith('.tgz') or bfnl.endswith('.tar'):
        yield fns, None, FileType.ARCHIVE
        with TarFile.open(fileobj=fh) as tf:
            for ti in tf.getmembers():
                newname = (*fns, PurePosixPath(ti.name))
                if ti.issym(): yield newname, None, FileType.SYMLINK
                elif ti.isdir(): yield newname, None, FileType.DIR
                elif ti.isfile():
                    # Note apparently this uses a lot of memory: https://github.com/python/cpython/issues/102120
                    with tf.extractfile(ti) as fh2:
                        yield from _procfile(newname, fh2)
                else: yield newname, None, FileType.OTHER  # for ti.type see e.g.: https://github.com/python/cpython/blob/v3.11.1/Lib/tarfile.py#L87
    elif bfnl.endswith('.zip'):
        yield fns, None, FileType.ARCHIVE
        with ZipFile(fh) as zf:
            for zi in zf.infolist():
                # Note the ZIP specification requires forward slashes for pathnames.
                # https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
                newname = (*fns, PurePosixPath(zi.filename))
                # Manually detect symlinks in ZIP files (should be rare anyway)
                # e.g. from zipfile.py: zinfo.external_attr = (st.st_mode & 0xFFFF) << 16
                # we're not going to worry about other special file types in ZIP files
                if zi.create_system==3 and stat.S_ISLNK(zi.external_attr>>16):  # 3 is UNIX
                    yield newname, None, FileType.SYMLINK
                elif zi.is_dir(): yield newname, None, FileType.DIR
                else:  # (note this interface doesn't have an is_file)
                    with zf.open(zi) as fh2:
                        yield from _procfile(newname, fh2)
    elif bfnl.endswith('.gz'):
        yield fns, None, FileType.ARCHIVE
        with GzipFile(fileobj=fh, mode='rb') as fh2:
            yield from _procfile((*fns, fns[-1].with_suffix('')), fh2)
    else:
        yield fns, fh, FileType.FILE

def unzipwalk(paths :AnyPaths, *, onlyfiles :bool=True) \
        -> Generator[ tuple[ tuple[PurePath, ...], Optional[typing.IO[bytes]], FileType ], None, None ]:
    """Recursively step into directories and compressed files and yield names and filehandles.

    This generator yields tuples consisting of the elements:

    1. A tuple of the filename(s) as ``pathlib`` objects. If this tuple has only one element, then the yielded file
       physically exists in the filesystem, and if the tuple has more than one element, then the yielded file is
       contained in a compressed file, possibly nested in other compressed file(s), and the last element of the
       tuple will contain the file's actual name.
    2. The filehandle for reading the file contents, open in binary mode. *However,* if ``onlyfiles`` is ``False``
       and the file type is anything other than ``FileType.FILE``, this element will be ``None``.
       Whether this filehandle supports operations like seeking depends on the underlying library.
    3. A ``FileType`` value representing the type of the current file.
       When ``onlyfiles`` is ``True`` (the default), this will always be ``FileType.FILE``.

    The yielded filehandles can for example be wrapped in ``io.TextIOWrapper`` to read them as text files,
    or even CSV files, for example:

        >>> from io import TextIOWrapper
        >>> import csv
        >>> for fnames, binfhnd, _ in unzipwalk('.'):
        ...     if fnames[-1].suffix.lower() == '.csv':
        ...         with TextIOWrapper(binfhnd, 'UTF-8', newline='') as fhnd:
        ...             print(repr(fnames))
        ...             csvrd = csv.reader(fhnd, strict=True)
        ...             for row in csvrd: print(repr(row))           # doctest:+ELLIPSIS
        (...)
        [...]

    Currently supported are ZIP, tar, tar+gz, and gz compressed files.
    """
    ppaths = tuple(to_Paths(paths))
    for p in ppaths: p.resolve(strict=True)  # force FileNotFound errors early
    for p in chain.from_iterable( pa.rglob('*') if pa.is_dir() else (pa,) for pa in ppaths ):
        if p.is_symlink():
            if not onlyfiles: yield (p,), None, FileType.SYMLINK
        elif p.is_dir():
            if not onlyfiles: yield (p,), None, FileType.DIR
        elif p.is_file():
            with p.open('rb') as fh:
                yield from ( f for f in _procfile((p,), fh) if f[2]==FileType.FILE ) if onlyfiles else _procfile((p,), fh)
        else:
            if not onlyfiles: yield (p,), None, FileType.OTHER

if __name__ == '__main__':  # pragma: no cover
    import sys
    import argparse
    import errorutils
    errorutils.init_handlers()
    parser = argparse.ArgumentParser(description='unzipwalk')
    parser.add_argument('-a','--allfiles',help="also list dirs, symlinks, etc.",action="store_true")
    parser.add_argument('-d','--dump',help="also dump file contents",action="store_true")
    parser.add_argument('paths', metavar='PATH', help='paths', nargs='*')
    args = parser.parse_args()
    thepaths = args.paths if args.paths else Path()
    if args.allfiles:
        for filenames, handle, ftype in unzipwalk(thepaths, onlyfiles=False):
            if args.dump and ftype==FileType.FILE:
                print(f"{filenames!r} {ftype} {handle.read()!r}")
            else: print(f"{filenames!r} {ftype}")
    else:
        for filenames, handle, _ in unzipwalk(thepaths):
            if args.dump: print(f"{filenames!r} {handle.read()!r}")
            else: print(f"{filenames!r}")
    sys.exit(0)
