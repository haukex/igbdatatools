#!python3
"""Library with some file-related utility functions.

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
import os
import stat
import sys
from pathlib import Path
from contextlib import contextmanager
from functools import singledispatch
from tempfile import NamedTemporaryFile
from collections.abc import Generator, Iterable

Filename = str|os.PathLike

AnyPaths = Filename|bytes|Iterable[Filename|bytes]
@singledispatch
def _topath(item :Filename|bytes):
    raise TypeError(f"I don't know how to covert this to a Path: {item!r}")
@_topath.register
def _(item :bytes): return Path(os.fsdecode(item))
@_topath.register
def _(item :Filename): return Path(item)
# noinspection PyPep8Naming
@singledispatch
def to_Paths(paths :AnyPaths) -> Generator[Path, None, None]:
    """Convert various inputs to ``pathlib.Path`` objects."""
    yield from map(_topath, iter(paths))
@to_Paths.register
def _(paths :Filename|bytes) -> Generator[Path, None, None]:
    yield _topath(paths)

def autoglob(files :Iterable[str], *, force :bool=False) -> Generator[str, None, None]:
    """In Windows, automatically apply ``glob`` and ``expanduser``, otherwise don't change the input."""
    from glob import glob
    from os.path import expanduser
    if sys.platform.startswith('win32') or force:
        for f in files:
            f = expanduser(f)
            g = glob(f)  # note glob always returns a list
            # If a *NIX glob doesn't match anything, it isn't expanded,
            # while glob() returns an empty list, so we emulate *NIX.
            if g: yield from g
            else: yield f
    else:
        yield from files

class Pushd:  # pragma: no cover
    """A context manager that temporarily changes the current working directory."""
    def __init__(self, newdir :Filename):
        self.newdir = newdir
    def __enter__(self):
        self.prevdir = os.getcwd()
        os.chdir(self.newdir)
        return
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.prevdir)
        return False  # raise exception if any
if sys.hexversion>=0x030B00F0:  # available as of Python 3.11
    import contextlib
    Pushd = contextlib.chdir  #TODO Later: can probably deprecate our Pushd in favor of this
else: pass  # pragma: no cover

def filetypestr(st :os.stat_result) -> str:
    """Return a string naming the file type reported by ``stat``."""
    if stat.S_ISDIR(st.st_mode): return "directory"
    elif stat.S_ISCHR(st.st_mode): return "character special device file"  # pragma: no cover
    elif stat.S_ISBLK(st.st_mode): return "block special device file"  # pragma: no cover
    elif stat.S_ISREG(st.st_mode): return "regular file"
    elif stat.S_ISFIFO(st.st_mode): return "FIFO (named pipe)"
    elif stat.S_ISLNK(st.st_mode): return "symbolic link"
    elif stat.S_ISSOCK(st.st_mode): return "socket"  # pragma: no cover
    # Solaris
    elif stat.S_ISDOOR(st.st_mode): return "door"  # pragma: no cover
    # Solaris?
    elif stat.S_ISPORT(st.st_mode): return "event port"  # pragma: no cover
    # union/overlay file systems
    elif stat.S_ISWHT(st.st_mode): return "whiteout"  # pragma: no cover
    else: raise ValueError(f"unknown filetype {st.st_mode:#o}")  # pragma: no cover

invalidchars = frozenset( '<>:"/\\|?*' + bytes(range(32)).decode('ASCII') )
invalidnames = frozenset(( 'CON', 'PRN', 'AUX', 'NUL',
    'COM0', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT0', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9' ))
def is_windows_filename_bad(fn :str) -> bool:
    """Check whether a Windows filename is invalid.

    Tests whether a filename contains invalid characters or has an invalid name, but
    does *not* check whether there are name collisions between filenames of differing case.

    Reference: https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
    """
    return ( bool( set(fn).intersection(invalidchars) )  # invalid characters and names
        or fn.upper() in invalidnames
        # names are still invalid even if they have an extension
        or any( fn.upper().startswith(x+".") for x in invalidnames )
        # filenames shouldn't end on a space or period
        or fn[-1] in (' ', '.') )

@contextmanager
def replacer(file :Filename, *, binary :bool=False, encoding=None, errors=None, newline=None):
    """Replace a file by renaming a temporary file over the original.

    With this context manager, a temporary file is created in the same directory as the original file.
    The context manager gives you two file handles: the input file, and the output file, the latter
    being the temporary file. You can then read from the input file and write to the output file.
    When the context manager is exited, it will replace the input file over the temporary file.
    Depending on the OS and file system, this ``os.replace`` may be an atomic operation.
    If an error occurs in the context manager, the temporary file is unlinked and the original file left unchanged.
    """
    fname = Path(file).resolve(strict=True)
    if not fname.is_file(): raise ValueError(f"not a regular file: {fname}")
    with fname.open(mode = 'rb' if binary else 'r', encoding=encoding, errors=errors, newline=newline) as infh:
        origmode = stat.S_IMODE( os.stat(infh.fileno()).st_mode )
        with NamedTemporaryFile( dir=fname.parent, prefix="."+fname.name+"_", delete=False,
            mode = 'wb' if binary else 'w', encoding=encoding, errors=errors, newline=newline) as tf:
            try:
                yield infh, tf
            except BaseException:
                tf.close()
                os.unlink(tf.name)
                raise
    # note because any exceptions are reraised above, we can only get here on success:
    try: os.chmod(tf.name, origmode)
    except NotImplementedError: pass  # pragma: no cover
    os.replace(tf.name, fname)
