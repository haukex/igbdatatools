#!/usr/bin/env python
"""Parser for "time delta" strings.

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

_split_re = re.compile(r'''(?<=[dhms])\s*(?=[0-9])|(?<=[0-9])\s+(?=[0-9])''', re.IGNORECASE)
_detla_re = re.compile(r'''\A\s*(\d+)\s*([dhms]?)\s*\Z''', re.IGNORECASE)

def deltaparse(string :str) -> int:
    """Parse a "time delta" string into seconds.
    
    Parses strings such as "2h 5m", "5d 30h 5s", etc. into seconds. Values
    without units are considered seconds. Values are summed, e.g. "40 5d 3h 2d
    2s" is the same as "7d 3h 42s".
    """
    delta_s = 0
    if string.isspace(): return 0
    for part in _split_re.split(string):
        if m := _detla_re.fullmatch(part):
            if   m.group(2).lower() == "d": delta_s += int(m.group(1))*60*60*24
            elif m.group(2).lower() == "h": delta_s += int(m.group(1))*60*60
            elif m.group(2).lower() == "m": delta_s += int(m.group(1))*60
            else:                           delta_s += int(m.group(1))
        else: raise ValueError("invalid delta string")
    return delta_s

if __name__ == '__main__':  # pragma: no cover
    import sys
    for x in sys.argv[1:]: print(f"{deltaparse(x)}")
    sys.exit(0)
