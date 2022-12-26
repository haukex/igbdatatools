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
from collections.abc import Generator, Iterable

AnyPaths = str|bytes|os.PathLike|Iterable[str|bytes|os.PathLike]
# noinspection PyPep8Naming
def to_Paths(paths :AnyPaths) -> Generator[Path]:
    """Convert various inputs to ``pathlib.Path`` objects."""
    def topath(item):
        if isinstance(item, str|bytes): return Path(os.fsdecode(item))
        elif isinstance(item, os.PathLike): return Path(item)
        else: raise TypeError(f"I don't know how to covert this to a Path: {item!r}")
    if isinstance(paths, str|bytes|os.PathLike): yield topath(paths)
    else: yield from map(topath, iter(paths))

def autoglob(files :Iterable[str], *, force :bool=False) -> Generator[str]:
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

class Pushd:
    """A context manager that temporarily changes the current working directory."""
    def __init__(self, newdir :str|os.PathLike):
        self.newdir = newdir
    def __enter__(self):
        self.prevdir = os.getcwd()
        os.chdir(self.newdir)
        return
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.prevdir)
        return False  # raise exception if any

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
