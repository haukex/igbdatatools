#!/usr/bin/env python3
"""Various Unicode related utility functions.

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
import sys
import re
from typing import NamedTuple
from itertools import chain
import unicodedata
from collections.abc import Generator, Iterable
# the module resides in the package pyicu, but PyCharm doesn't seem to correctly detect that
# noinspection PyPackageRequirements
from icu import BreakIterator, Locale, UnicodeString

def graphemeclusters(text :str|UnicodeString, *, locale=Locale.getRoot()) -> Generator[str]:
    """Break a string into grapheme clusters.

    References:

    - http://www.unicode.org/reports/tr29/#Grapheme_Cluster_Boundaries
    - https://unicode-org.github.io/icu/userguide/boundaryanalysis/
    - https://unicode-org.github.io/icu-docs/apidoc/released/icu4c/classicu_1_1BreakIterator.html
    - https://gitlab.pyicu.org/main/pyicu/-/blob/main/samples/break.py
    """
    if not isinstance(text, UnicodeString):
        text = UnicodeString(text)
    bi = BreakIterator.createCharacterInstance(locale)
    bi.setText(text)
    start = bi.first()
    assert start==0
    end = 0
    for end in bi:
        yield str(text[start:end])
        start = end
    assert end == len(text)

common_ascii = bytes(chain((0x09, 0x0A, 0x0D), range(0x20, 0x7F))).decode("ASCII")
def is_common_ascii_char(char :str) -> bool:
    """Return whether the given character is CR, LF, Tab, or printable ASCII."""
    return len(char)==1 and char in common_ascii

def format_unichars(chars :str) -> str:
    """Format a string into its code points, including character names.

    Intended mostly for use on single characters or grapheme clusters."""
    return ' + '.join( f"U+{ord(c):04X} {unicodedata.name(c, '(unnamed)')}" for c in chars )

DEFAULT_ENCODINGS = ('ASCII', 'UTF-8', 'ISO-8859-1', 'CP1252')
def try_encodings(data :bytes, *, encodings :Iterable[str]=DEFAULT_ENCODINGS) -> Generator[str]:
    """Attempt to decode bytes using different encodings, and report the working encodings.

    Note a more comprehensive library to guess encodings is: https://pypi.org/project/chardet/"""
    for enc in encodings:
        try: data.decode(enc, errors='strict')
        except UnicodeError: pass
        else: yield enc

# Possible To-Do for Later: I currently don't see an easier way to get characters by properties?
_otherctrl = { c for c in map(chr, range(sys.maxunicode+1)) if unicodedata.category(c)=='Cc' } - set("\x00\x09\x0A\x0D")
_cr_re = re.compile(r'''\x0D(?!\x0A)''')
_lf_re = re.compile(r'''(?<!\x0D)\x0A''')
class ControlCharReport(NamedTuple):
    """You can use this class's ``from_text`` to scan a string and count the Unicode control characters in that string.

    Use ``str(report)`` to get a stringified report.

    Note ``ctrl`` does not include NUL, CR, LF, or Tab."""
    cr :int
    lf :int
    crlf :int
    nul :int
    ctrl :int
    @staticmethod
    def from_text(text :str) -> 'ControlCharReport':
        return ControlCharReport(
            cr = len(_cr_re.findall(text)),
            lf = len(_lf_re.findall(text)),
            crlf = text.count("\x0D\x0A"),
            nul = text.count("\x00"),
            ctrl = sum( 1 for c in text if c in _otherctrl )
        )
    def __str__(self):
        o = []
        if self.nul: o.append(f"{self.nul} NULs")
        if self.ctrl: o.append(f"{self.ctrl} CTRLs (excl NUL/CR/LF/Tab)")
        if self.cr or self.lf or self.crlf:
            if self.cr and self.lf or self.crlf and (self.cr or self.lf):
                o.append("MIXED CR/LF")
            if self.cr: o.append(f"{self.cr} CRs")
            if self.lf: o.append(f"{self.lf} LFs")
            if self.crlf: o.append(f"{self.crlf} CRLFs")
        else: o.append('no CR or LF')
        return ', '.join(o)

if __name__ == '__main__':  # pragma: no cover
    import sys
    import os
    import argparse
    import errorutils
    from unidecode import unidecode
    errorutils.init_handlers()
    parser = argparse.ArgumentParser(description='Unicode Utilities')
    parser.add_argument('-a','--allencodings',help="Report all matching encodings, not just the first",action="store_true")
    parser.add_argument('-e','--enc',dest='encodings',metavar="ENCODING",
        help="Use this encoding instead of the defaults (can specify multiple)",action="append")
    parser.add_argument('-c','--chars',help="Split file into characters instead of grapheme clusters",action="store_true")
    parser.add_argument('-L','--no-list',help="Don't list Unicode graphemes/characters",action="store_true")
    parser.add_argument('-s','--size-limit',help="File size limit in bytes (default 10e6, 0=off)",metavar="BYTES",type=float,default=10e6)
    parser.add_argument('files', metavar='FILE', help='input files', nargs='+')
    args = parser.parse_args()
    if args.size_limit<0: raise ValueError("--size-limit must be positive")
    if args.no_list and args.chars: raise ValueError("--chars doesn't make sense with --no-list")
    tryencs = tuple(args.encodings) if args.encodings else DEFAULT_ENCODINGS
    for file in args.files:
        size = os.stat(file).st_size
        if args.size_limit and size > args.size_limit:
            print(f"Skipping {file!r} ({size} bytes)")
            continue
        with open(file,'rb') as fh: fdata = fh.read()
        if args.allencodings:
            gotencs = tuple(try_encodings(fdata, encodings=tryencs))
        else:
            try: gotencs = (next(try_encodings(fdata, encodings=tryencs)),)
            except StopIteration: gotencs = ()
        if gotencs:
            ftext = fdata.decode(gotencs[0])
            print(f"{file}: Valid {', '.join(gotencs)}, {ControlCharReport.from_text(ftext)}")
            if args.no_list: continue
            for grph in ftext if args.chars else graphemeclusters(ftext):
                if is_common_ascii_char(grph): continue
                nfcs=''
                udec=''
                if not args.chars:
                    nfc = unicodedata.normalize('NFC', grph)
                    if nfc!=grph: nfcs = f" (NFC: {format_unichars(nfc)})"
                    if unidecode(nfc): udec = f" ({unidecode(nfc)})"
                print(f"\t\"{grph}\" {format_unichars(grph)}{nfcs}{udec}")
        else:
            print(f"{file}: INVALID {', '.join(tryencs)}")
    sys.exit(0)
