#!python3
"""Test whether two decimal numbers are off-by-one on their least significant digit.

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
import re

_decimal_re = re.compile(r"""\A\d+\.\d+\Z""")

def lsb_obo(a :str, b :str) -> bool:
    """Test whether two decimal numbers stored as strings are off-by-one on their least significant digit."""
    # This implementation is not particularly efficient but since it's currently only used in debugging it's fine.
    if not _decimal_re.fullmatch(a):
        if a.isdecimal(): a += ".0"
        else: raise ValueError(f"Can't handle string in this format: {a!r}")
    if not _decimal_re.fullmatch(b):
        if b.isdecimal(): b += ".0"
        else: raise ValueError(f"Can't handle string in this format: {b!r}")
    # pad on left
    ai = a.index('.')
    bi = b.index('.')
    if ai<bi:   a = "0"*(bi-ai) + a
    elif ai>bi: b = "0"*(ai-bi) + b
    # pad on right
    mlen = max(map(len, (a, b)))
    a = a.ljust(mlen, '0')
    b = b.ljust(mlen, '0')
    # checks
    assert _decimal_re.fullmatch(a)
    assert _decimal_re.fullmatch(b)
    assert len(a)==len(b)
    assert a.index('.')==b.index('.')
    # convert to int for comparison
    a = int(a.replace('.',''))
    b = int(b.replace('.',''))
    return abs(a-b)==1
