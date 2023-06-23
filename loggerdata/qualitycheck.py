#!python3
"""Basic Data Quality checking functions

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
from collections.abc import Iterable, Generator
from loggerdata.metadata import Interval
from itertools import pairwise
from enum import Enum
from math import isfinite
from datetime import datetime

class BasicQuality(Enum):
    GOOD = 0
    UNUSUAL = 1
    BAD = 2

# Note: 7999 is the max of Campbell's FP2 datatype (alternative is IEEE4)
# float(7999) and float(-7999) can be stored accurately as IEEE-754
DEFAULT_UNUSUAL = frozenset({ "", 7999, -7999, "7999", "-7999" })

def basic_quality(val, *, unusualvals :set = DEFAULT_UNUSUAL) -> BasicQuality:
    """Does some simply quality checks on the data value."""
    if val is None:
        return BasicQuality.BAD
    elif isinstance(val, str):
        if val.lower()=='nan': return BasicQuality.BAD
        return BasicQuality.UNUSUAL if val.isspace() or val in unusualvals else BasicQuality.GOOD
    elif isinstance(val, bool|int|float):
        if not isfinite(val): return BasicQuality.BAD
        return BasicQuality.UNUSUAL if val in unusualvals else BasicQuality.GOOD
    elif isinstance(val, datetime):
        return BasicQuality.GOOD
    elif isinstance(val, complex):
        return BasicQuality.UNUSUAL
    return BasicQuality.BAD

def check_timeseq_strict(seq :Iterable[datetime], *, interval :Interval) -> Generator[bool, None, None]:
    """Checks whether the given sequence is strictly monotonically increasing according to the given ``Interval``,
    returning ``True`` or ``False`` for each item in the sequence."""
    for i, (x, y) in enumerate(pairwise(seq)):
        if i==0: yield x == interval.floor(x)
        yield y == interval.floor(y) and y == interval.floor(x) + interval.delta
