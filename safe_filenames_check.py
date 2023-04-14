#!/usr/bin/env python3
"""Utility to check for Windows-safe filenames.

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
from collections import defaultdict
from collections.abc import Generator
from pathlib import Path, PurePath
from unzipwalk import unzipwalk, FileType
import uniutils
from igbpyutils.file import AnyPaths, filetypestr, is_windows_filename_bad, invalidchars

_base_allowed_chars = frozenset( set(uniutils.common_ascii) - invalidchars )

def list_problems(paths :AnyPaths, *, ignore_compressed :bool = False, ignore_symlinks :bool = False,
        allowed_chars :set[str] = None ) -> Generator[tuple[tuple[PurePath, ...], str], None, None]:
    """This function walks a directory tree, including entering compressed files, and checks whether all filenames
    encountered are safe to use in a Windows environment.

    This generator yields a tuple for each problem found. The first element is a tuple of filenames like the
    one returned by ``unzipwalk``. The second element is a string describing the problem.

    ``allowed_chars`` may be a set of characters which are allowed in filenames in addition to basic ASCII."""
    allowed = _base_allowed_chars
    if allowed_chars: allowed |= allowed_chars
    collections :dict[tuple[PurePath, ...], set[str]] = defaultdict(set)
    for fns,bfh,fty in unzipwalk(paths, onlyfiles=False):
        thefn = fns[-1]
        # ##### ##### Type Check ##### #####
        if len(fns)==1:  # a physical file in the filesystem that we can stat
            st = Path(thefn).lstat()
            if hasattr(st,'st_file_attributes') and st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:  # pragma: no cover
                # Windows: "A file or directory that has an associated reparse point, or a file that is a symbolic link."
                yield fns, "reparse point or symbolic link"
                # Possible To-Do for Later: could also warn on other special Windows file types?
            elif stat.S_ISLNK(st.st_mode):
                if not ignore_symlinks: yield fns, "symlink"
            elif stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode): pass
            else: yield fns, filetypestr(st)
            # ##### ##### Name Check ##### #####
            # For physical files, we know unzipwalk will report every entry,
            # so it's fine to just check the filename ...
            names_to_check = (thefn.name,)
        else:  # compressed
            assert len(fns)>1
            if ignore_compressed: continue
            # ... however, in compressed files, it's possible for files inside of directories
            # to show up without there being an entry for the directory.
            names_to_check = thefn.parts
            # ### A brief Type Check interjection
            if fty not in (FileType.FILE, FileType.ARCHIVE, FileType.DIR):
                if not ( ignore_symlinks and fty==FileType.SYMLINK ):
                    yield fns, str(fty)
        for name in names_to_check:
            if is_windows_filename_bad(name):
                yield fns, f"filename not allowed in Windows: {name!r}"
            elif unichars := tuple( sorted( set(uniutils.graphemeclusters(name)) - allowed ) ):
                # Possible To-Do for Later: report NFC form and/or unidecode form
                # For example, if `allowed` contains "\N{LATIN SMALL LETTER A WITH DIAERESIS}",
                # but the filename contains "a\N{COMBINING DIAERESIS}", that could be reported
                yield fns, f"non-ASCII characters {unichars!r}"
        # ##### ##### Case Check ##### #####
        loc = fns[0:-1]
        allcases = {str(thefn).upper(), str(thefn).lower(), str(thefn).casefold()}  # a bit overkill but whatever
        if coll := collections[loc] & allcases:
            yield fns, f"case collision in {loc!r}: {sorted(coll)!r}"
        collections[loc] |= allcases

if __name__ == '__main__':  # pragma: no cover
    import sys
    import argparse
    from igbpyutils.file import autoglob
    parser = argparse.ArgumentParser(description='Check for Bad Filenames/types')
    parser.add_argument('-L', '--ignore-symlinks', help="ignore symlinks", action="store_true")
    parser.add_argument('-Z', '--ignore-compressed', help="ignore compressed files", action="store_true")
    parser.add_argument('-a', '--allowed-chars', help="a set of allowed characters", action="append", default=[])
    parser.add_argument('--german', help="add German umlauts and SZ to allowed characters", action="store_true")
    parser.add_argument('--french', help="add French diacritics etc. to allowed characters", action="store_true")
    parser.add_argument('--spanish', help="add Spanish diacritics etc. to allowed characters", action="store_true")
    parser.add_argument('paths', help="paths to check", nargs="*")
    args = parser.parse_args()
    pths = autoglob(args.paths) if args.paths else Path()
    allowedchars = set(''.join(args.allowed_chars))
    if args.german: allowedchars |= set("äüöÄÜÖßẞÉé")  # added eacute for e.g. Café (somewhat common in German)
    # excluded Ææ in the following because it's rare in French but somewhat common in Mojibake
    if args.french: allowedchars |= set("ÀàÂâÇçÉéÈèÊêËëÎîÏïÔôŒœÙùÛûÜüŸÿ")
    if args.spanish: allowedchars |= set("ÑñáéíóúýüÁÉÍÓÚÝÜ")
    for pth,reason in list_problems(pths, ignore_compressed=args.ignore_compressed,
                                    ignore_symlinks=args.ignore_symlinks, allowed_chars=allowedchars):
        print(f"{tuple(map(str, pth))}: {reason}")
    sys.exit(0)
