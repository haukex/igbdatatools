#!python
"""A library for representing files together with their hashes.

Author, Copyright, and License
------------------------------
Copyright (c) 2022-2023 Hauke Daempfling (haukex@zero-g.net)
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
import re
import hashlib
import operator
from enum import Enum
from typing import Self, NamedTuple, Optional
from collections.abc import Iterable, Generator
from igbpyutils.file import Filename

def _algo_from_hashsize(hsh :bytes):
    match len(hsh):
        case 64: return hashlib.sha512
        case 48: return hashlib.sha384
        case 32: return hashlib.sha256
        case 28: return hashlib.sha224
        case 20: return hashlib.sha1
        case 16: return hashlib.md5
    raise ValueError(f"hash has unknown length: {hsh!r}")

_hashline_re = re.compile( r''' \A (?P<hash> [0-9a-fA-F]+ ) \  (?P<bin> [* ]) (?P<fn> \S.* ) \r?\n? \Z ''', re.X)

# NOTE changing this won't affect the usages below (see comments there)! so I suggest not changing this
DEFAULT_HASH = hashlib.sha512

class HashedFile(NamedTuple):
    """Represents and provides utility methods for hashed files.

    It is *strongly recommended* to use ``from_file`` and ``from_line`` instead of the normal constructor.

    Note ``binflag`` has no real meaning and is provided only for compatibility with the ``sha*sum`` commands and proper
    round-tripping of lines. This code always reads files in binary mode, and I have so far not come across any tool
    that hashes files in "text" mode (which has no meaning on *NIX anyway).

    ``binflag`` and ``valid`` are not used in equality checks or the object's hash. ``fn`` is always stringified for
    equality checks and the object's hash."""
    fn: Filename
    hsh: bytes
    binflag: bool = True
    valid: Optional[bool] = None

    # NOTE algo=DEFAULT_HASH gets evaluated only once, so changing DEFAULT_HASH doesn't change the default algo here!
    @classmethod
    def from_file(cls, file :Filename, *, algo=DEFAULT_HASH) -> Self:
        """Hash a file and return the corresponding object."""
        return cls(fn=file, hsh=cls.hash_file(file, algo=algo), binflag=True, valid=True)

    @classmethod
    def from_line(cls, line :str, *, binflag :Optional[bool]=None) -> Self:
        """Parse a line into an object.

        The ``binflag`` argument can be used to override the flag found in the line."""
        if m := _hashline_re.fullmatch(line):
            hsh = bytes.fromhex(m['hash'])
            _algo_from_hashsize(hsh)
            return cls( fn = m['fn'], hsh = hsh, valid = None,
                        binflag = bool(binflag) if binflag is not None else m['bin']=='*' )
        else: raise ValueError(f"failed to parse line {line!r}")

    def __eq__(self, other):
        return str(self.fn) == str(other.fn) and self.hsh == other.hsh
    def __ne__(self, other):
        return str(self.fn) != str(other.fn) or self.hsh != other.hsh
    def __hash__(self):
        return hash((str(self.fn), self.hsh))

    def to_line(self) -> str:
        """Return a line representing this object."""
        return self.hsh.hex() + " " + ("*" if self.binflag else " ") + str(self.fn)

    def validate(self, *, force :bool=False, fail_soft :bool=False) -> Self|tuple[Self, bytes]:
        """Validate whether this object's hash matches the hash of the file in the filesystem.

        Does **not** modify this object but returns a new one!

        If you set ``fail_soft``, then on success, this function will return a two-item tuple consisting of
        the original object with ``valid`` set to ``False``, and the hash that was calculated from the file.
        *Warning:* If ``fail_soft`` is true and ``force`` is false, and this object's ``valid`` flag is
        already set to ``True``, then no hashing on the disk is performed, and the second item of the returned
        tuple will simply be this hash's precomputed hash value. To always go out to the disk, set ``force``.

        The ``binflag`` is ignored and not modified."""
        if self.valid and not force:
            if fail_soft: return self, self.hsh
            else: return self
        gothsh = self.hash_file(self.fn, algo=self.algo)
        if gothsh != self.hsh:
            if fail_soft: return self._replace(valid=False), gothsh
            else: raise ValueError(f"failed to validate {self.fn}: expected {self.hsh.hex()}, got {gothsh.hex()}")
        else:
            if fail_soft: return self._replace(valid=True), gothsh
            else: return self._replace(valid=True)

    @property
    def algo(self):
        """Return the hash algorithm used for this hash (based on the length of ``hsh``)."""
        return _algo_from_hashsize(self.hsh)

    def setfn(self, fn :Filename) -> Self:
        """Return a new object with the filename replaced.

        Intended for e.g. converting the filename from absolute to relative or vice versa.
        **Warning:** Changing the filename to point to a different file will likely lead to confusion!"""
        return self._replace(fn=fn)

    def rehash(self, *, algo=None) -> Self:
        """Recalculate the hash of the file represented by this object.

        Returns a **new** object."""
        return type(self).from_file(self.fn, algo = self.algo if algo is None else algo )

    # NOTE algo=DEFAULT_HASH gets evaluated only once, so changing DEFAULT_HASH doesn't change the default algo here!
    @staticmethod
    def hash_file(file :Filename, *, algo=DEFAULT_HASH) -> bytes:
        """Hashes a file."""
        h = algo()
        mv = memoryview( bytearray( io.DEFAULT_BUFFER_SIZE ) )
        fh :io.RawIOBase
        with open(file, 'rb', buffering=0) as fh:
            while n := fh.readinto(mv):
                h.update(mv[:n])
        return h.digest()

def hashes_to_file(file :Filename, hashes :Iterable[HashedFile]) -> int:
    """Write a list of ``HashedFile``s to a text file."""
    count = 0
    with open(file, 'w', encoding='UTF-8', newline="\n") as fh:
        for h in hashes:
            print(h.to_line(), file=fh)
            count += 1
    return count

def hashes_from_file(file :Filename) -> Generator[HashedFile, None, None]:
    """Read a list of ``HashedFile``s from a text file."""
    with open(file, encoding='UTF-8') as fh:
        for line in fh:
            yield HashedFile.from_line(line)

class SortingType(Enum):
    """Argument for :func:`sort_hashed_files`."""
    NO_SORT = 0
    BY_LINE = 1
    BY_HASH = 2
    BY_FILE = 3

def sort_hashedfiles(hfs :Iterable[HashedFile], sort :SortingType) -> Generator[HashedFile, None, None]:
    """Sort ``HashedFile``s by different schemes.

    Note that for all ``SortingType``s other than ``NO_SORT``, ``sorted``
    has to consume the entire input before producing the output, however,
    ``sorted`` isn't run until this generator is actually run for the first time.

    The difference between ``BY_HASH`` and ``BY_LINE`` is that the latter sorts
    on hashes first and filenames second, while ignoring ``HashedFile.binflag``.
    """
    if sort==SortingType.NO_SORT: yield from hfs
    elif sort==SortingType.BY_LINE: yield from sorted(hfs, key=operator.itemgetter(1, 0))
    elif sort==SortingType.BY_HASH: yield from sorted(hfs, key=operator.itemgetter(1))
    elif sort==SortingType.BY_FILE: yield from sorted(hfs, key=operator.itemgetter(0))
    else: raise ValueError(repr(sort))
