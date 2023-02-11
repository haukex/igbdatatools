#!/usr/bin/env python3
"""File checksumming tool.

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
import stat
from collections.abc import Generator, Iterable
from itertools import chain
from pathlib import Path, PurePath
from typing import NamedTuple, Self, Optional
from ordered_enum import OrderedEnum
from more_itertools import unique_everseen, partition
from hashedfile import HashedFile, hashes_from_file, hashes_to_file, DEFAULT_HASH
from fileutils import to_Paths, AnyPaths, filetypestr

class ResultCode(OrderedEnum):  # this needs to be ordered so that FileResults can be sorted
    """A status code for ``FileResult``s."""
    NONE = 0
    SKIP = 1
    NEEDSVALIDATE = 2
    SUMOK = 3
    BADINPUT = 4
    SUMMISMATCH = 5
    NOSUM = 6
    MISSING = 7
    DUPEFN = 8  # note: only happens when ignorepath is on
    UNKNOWN = 9

class FileResult(NamedTuple):
    """A class representing results of checksum processing.

    These objects are returned by :func:`list_hashable_files` and further processed by
    :func:`match_hashes` and :func:`check_hashes`, see those functions for details.

    ``fn`` may be the result of ``Path.resolve``, or it may be the original filename.
    ``origfn`` is the original filename that is passed through for nicer display to the user.
    """
    fn :PurePath
    origfn :str
    code :ResultCode
    hsh :Optional[HashedFile] = None
    msg :Optional[str] = None

    def hash_me(self, *, check_code :bool=True, algo=DEFAULT_HASH) -> Self:
        """Returns a new object with the ``hsh`` field populated (if it hasn't been populated before).

        If ``check_code`` is enabled (the default), this function will also check the ``code`` and make sure it's
        a normal hashable file and raise an exception otherwise, and ``SKIP``s are not hashed.
        Only the ``hsh`` field is modified by this function, not ``code`` or any other fields.
        """
        if check_code and self.code == ResultCode.SKIP:
            return self
        elif check_code and self.code not in (ResultCode.NONE, ResultCode.SUMOK):
            raise ValueError(f"ResultCode was not NONE, SKIP, or SUMOK: {self!r}")
        else:
            if self.hsh and self.hsh.valid and algo==self.hsh.algo:
                return self
            return self._replace( hsh = HashedFile.from_file(self.fn, algo=algo).setfn( PurePath(self.origfn) ) )

def list_hashable_files(paths :AnyPaths, *, report_dirs :bool=False, skip_win_hidden :bool=False) -> Generator[FileResult]:
    # noinspection PyShadowingNames, PyUnresolvedReferences
    """This function lists all directory entries it consideres hashable in a set of paths.

    "Hashable" currently just means "regular files", i.e. no symlinks, FIFOs, etc.

    This function will only yield ``FileResult``s with the ``ResultCode``s ``NONE`` (hashable)
    or ``SKIP`` (not hashable). There will be no duplicates in the files with a ``NONE`` ``ResultCode``,
    but there may be duplicate entries returned for ``SKIP`` files, especially if there were duplicates
    in the set of input files.

    Here is how to generate a list of ``HashedFiles`` using this function:

    >>> [ fr.hash_me().hsh for fr in list_hashable_files(paths) if fr.code != ResultCode.SKIP ]
    """
    seen = set()
    for p in chain.from_iterable( pa.rglob('*') if pa.is_dir() else (pa,) for pa in to_Paths(paths) ):
        st = p.lstat()
        if hasattr(st, 'st_file_attributes') and st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:  # pragma: no cover
            # Windows: "A file or directory that has an associated reparse point, or a file that is a symbolic link."
            yield FileResult(fn=p, origfn=str(p), code=ResultCode.SKIP, msg=f"skipping reparse point {p}")
        elif skip_win_hidden and hasattr(st, 'st_file_attributes') and st.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:  # pragma: no cover
            # Windows: "The file or directory is hidden. It is not included in an ordinary directory listing."
            # Note: A Windows virus scanner (Cyvera/Palo Alto Cortex) injects a bunch of fake files into listings under pythonw.exe.
            # Most of these are hidden, but because on *NIX "hidden" files aren't skipped and are checksummed,
            # the better workaround seems to be to use python.exe instead, where this doesn't seem to happen.
            yield FileResult(fn=p, origfn=str(p), code=ResultCode.SKIP, msg=f"skipping hidden {p}")
        elif stat.S_ISLNK(st.st_mode):
            # we don't want to add symlinks to the "seen" set, and showing "rp" doesn't make much sense in the message
            yield FileResult(fn=p, origfn=str(p), code=ResultCode.SKIP, msg=f"skipping symlink {p} -> {p.readlink()}")
        else:
            rp = p.resolve(strict=True)
            if rp in seen: continue
            seen.add(rp)
            if stat.S_ISDIR(st.st_mode):  # rglob above takes care descending into dirs
                if report_dirs:
                    yield FileResult(fn=rp, origfn=str(p), code=ResultCode.SKIP, msg=f"skipping directory {rp}")
            elif stat.S_ISREG(st.st_mode):
                # if the following assertion fails under Windows, see the above comment about the virus scanner
                assert rp.name == p.name  # because this is not a symlink
                yield FileResult(fn=rp, origfn=str(p), code=ResultCode.NONE)
            else:
                yield FileResult(fn=rp, origfn=str(p), code=ResultCode.SKIP, msg=f"skipping {filetypestr(st)} {rp}")

def check_hashes(source :Iterable[FileResult]) -> Generator[FileResult]:
    """This function validates the hashes as returned by :func:`match_hashes`.

    It will validate those ``FileResult``s with a ``ResultCode`` of ``NEEDSVALIDATE`` against the filesystem.
    It will return exactly one output item for each input item.
    Therefore, this iterator can be wrapped with a "progress meter" function if desired.
    """
    for fr in source:
        if fr.code == ResultCode.NEEDSVALIDATE:
            assert fr.hsh is not None and fr.msg is None  # just double-check the state of the object
            assert fr.hsh.valid is None
            # the "force" below isn't strictly needed because of the "assert" above, but we'll play it safe
            hsh2, gothsh = fr.hsh.validate(fail_soft=True, force=True)
            if hsh2.valid: yield fr._replace(hsh=hsh2, code=ResultCode.SUMOK)
            else: yield fr._replace(hsh=hsh2, code=ResultCode.SUMMISMATCH,
                    msg=f"checksum mismatch, calculated {gothsh.hex()}, expected {fr.hsh.hsh.hex()}")
        else:
            assert fr.code not in (ResultCode.NONE, ResultCode.SUMOK, ResultCode.SUMMISMATCH)
            assert fr.hsh is None
            yield fr

def match_hashes(*, sumsrc :Iterable[HashedFile], paths :AnyPaths, filesrc :Iterable[FileResult] = None,
                 ignorepath :bool = False) -> Generator[FileResult]:
    """This function matches a list of checksums against files in the filesystem.

    For filenames that match between the list of hashes and the filesystem,
    this function will *not* validate the hashes - the output of
    this function needs to be passed through :func:`check_hashes` for that!

    Normally, ``filesrc`` will be the output of :func:`list_hashable_files`
    (this is the default if this argument is not provided).
    The files returned by it *must* match the ``paths`` argument (which is needed to resolve filenames).
    The source must only contain ``FileResult``s with a ``ResultCode`` of ``SKIP`` or ``NONE``.

    This function will not return ``FileResult``s with a ``ResultCode`` of ``NONE``, ``SUMOK``, or ``SUMMISMATCH``.
    Note this function can't guarantee to return exactly one item per input item, as there are two sources of input.
    """
    paths = tuple( p.resolve(strict=True) for p in to_Paths(paths) )
    if not paths: raise ValueError("no paths given")
    # figure out the common parent directory of all paths
    commonparent = paths[0]
    while not all(map(lambda _: _.is_relative_to(commonparent), paths)) and commonparent.parent != commonparent:
        commonparent = commonparent.parent
    if not commonparent.is_dir():  # can happen if `paths` is a single filename, or one filename repeated multiple times
        commonparent = commonparent.parent
    unknowns :set[PurePath] = set()
    # gather all files
    if filesrc is None:
        filesrc = list_hashable_files(paths)
    files :dict[PurePath, FileResult] = {}
    for fr in filesrc:
        if fr.code==ResultCode.SKIP: yield fr; continue
        assert fr.code==ResultCode.NONE and fr.msg is None
        fn = PurePath(fr.fn.name) if ignorepath else fr.fn
        if fn in files:
            assert ignorepath  # because list_hashable_files doesn't return dupes (except SKIPs)
            unknowns.add(fn)
            yield fr._replace(fn=fn, code=ResultCode.DUPEFN, msg=f"filename appears more than once ({files[fn].fn} vs. {fr.fn})")
        files[fn] = fr
    # look at all checksums
    sums :dict[PurePath, HashedFile] = {}  # since 3.7: Dictionary order is guaranteed to be insertion order.
    for s in unique_everseen(sumsrc):
        fn = Path(s.fn)
        if ignorepath:
            fn = PurePath(fn.name)
        else:
            if not fn.is_absolute(): fn = commonparent/fn
            try: fn = fn.resolve(strict=True)
            except FileNotFoundError:
                yield FileResult(fn=fn, origfn=str(s.fn), code=ResultCode.MISSING, msg="file not found")
                continue
        if fn in sums:
            if sums[fn].hsh != s.hsh:
                unknowns.add(fn)
                yield FileResult(fn=fn, origfn=str(s.fn), code=ResultCode.BADINPUT,
                    msg=f"file appears more than once with differing checksums ({sums[fn].hsh.hex()} vs. {s.hsh.hex()})")
        else: sums[fn] = s
    # match up checksums with files
    for fn, s in sums.items():
        if fn in files:
            fr = files[fn]
            del files[fn]  # mark file seen
            assert ignorepath or fr.fn==fn
            if fn in unknowns:
                yield fr._replace(fn=fn, origfn=str(s.fn), code=ResultCode.UNKNOWN,
                    msg="can't reliably checksum file because it appears more than once in input")
            else:
                assert s.valid is None
                yield fr._replace(origfn=str(s.fn), hsh=s.setfn(fr.fn), code=ResultCode.NEEDSVALIDATE)
        else:
            yield FileResult(fn=fn, origfn=str(s.fn), code=ResultCode.MISSING, msg="file is missing")
    # check for leftover files
    for sfr in files.values():
        yield sfr._replace(code=ResultCode.NOSUM, msg="file has no checksum")

if __name__ == '__main__':  # pragma: no cover
    import sys
    import argparse
    from fileutils import autoglob
    from hashedfile import SortingType, sort_hashedfiles

    parser = argparse.ArgumentParser(description='File Hashing Tool')
    parser.add_argument('-q', '--quiet', help="less output", action="store_true")
    subparsers = parser.add_subparsers(dest='cmd', required=True)

    parser_gen = subparsers.add_parser('gen', help='generate hashes')
    parser_gen.add_argument('-o', '--outfile', help="output file")
    parser_gen.add_argument('-s', '--sort', help="sort output", action="store_true", default=False)
    parser_gen.add_argument('paths', help="paths to generate from", nargs="*")

    parser_check = subparsers.add_parser('check', help='check hashes')
    parser_check.add_argument('-p', '--ignorepath', help="ignore pathnames", action="store_true")
    parser_check.add_argument('sumfile', help="checksum file")
    parser_check.add_argument('paths', help="paths to check", nargs="*")

    args = parser.parse_args()

    if not args.quiet:
        from tqdm import tqdm
        from igbitertools import SizedCallbackIterator

    # list files
    allpaths = tuple( autoglob(args.paths) if args.paths else (Path(),) )
    thefilesgen = list_hashable_files(allpaths)  # get generator
    if not args.quiet:  # optionally wrap with progress bar
        thefilesgen = tqdm(thefilesgen, desc="Listing files...", unit=" files")
    thefiles = list(thefilesgen)  # now run the generator

    if args.cmd == 'gen':  # generate hashes
        hashes = ( fr.hash_me().hsh for fr in thefiles if fr.code != ResultCode.SKIP )  # set up generator
        if not args.quiet:  # optionally wrap with progress bar
            hashes = tqdm( SizedCallbackIterator(  # we know the generator will return one output per input item
                    it=hashes, length=sum( 1 for _ in thefiles if _.code != ResultCode.SKIP ), strict=True
                ), desc="Hashing files...", unit=" hashes")
        if args.sort:  # optionally sort - note the generator isn't run here, it still gets delayed until below
            hashes = sort_hashedfiles(hashes, SortingType.BY_LINE)
        # hash files and write output
        if args.outfile:
            count = hashes_to_file(args.outfile, hashes)
            if not args.quiet: print(f"Done, wrote {count} hashes to {args.outfile}", file=sys.stderr)
        else:
            count = 0
            for _hsh in hashes:
                print(_hsh.to_line())
                count += 1
            sys.stdout.flush()
            if not args.quiet: print(f"Done, wrote {count} hashes", file=sys.stderr)
    elif args.cmd == 'check':
        # read hashes from file
        hashesl = list(hashes_from_file(args.sumfile))
        # match hash list against the file list (already obtained from filesystem above)
        matched :Iterable[FileResult] = match_hashes(sumsrc=hashesl, filesrc=thefiles, paths=allpaths, ignorepath=args.ignorepath)
        if not args.quiet:  # optionally wrap with progress bar
            # only "NEEDSVALIDATE" files will really take processing time because those need to be hashed
            # so split the list into two iterators, put a progress bar on those files, and recombine
            noneed, needsvalid = partition(lambda _: _.code == ResultCode.NEEDSVALIDATE, matched)
            matched = chain(noneed, tqdm(list(needsvalid), desc="Checking hashes...", unit=" hashes"))
        errors = 0
        for r in check_hashes(matched):
            if r.code==ResultCode.SKIP or r.code==ResultCode.SUMOK: continue
            assert r.code != ResultCode.NONE
            print(f"{r.origfn}: {r.msg}")
            errors += 1
        sys.stdout.flush()
        if errors:
            if not args.quiet: print(f"Done, {errors} ERROR(s), checked {len(hashesl)} hashes against {len(thefiles)} files", file=sys.stderr)
            sys.exit(1)
        else:
            if not args.quiet: print(f"Done, no errors, checked {len(hashesl)} hashes against {len(thefiles)} files", file=sys.stderr)
    else:
        raise RuntimeError(repr(args.cmd))

    sys.exit(0)
