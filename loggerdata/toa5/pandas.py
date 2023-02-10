#!/usr/bin/env python3
"""Functions for reading TOA5 files into Pandas data frames.

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
import csv
from loggerdata.toa5 import read_header, Toa5Error
from loggerdata.metadata import ColumnHeader
import pandas

def toa5_to_pandas_dataframe(filename, *, csvnames :bool = True) -> pandas.DataFrame:
    """Read a TOA5 file into a Pandas data frame."""
    with open(filename, encoding='ASCII', newline='') as fh:
        envline, columns = read_header( csv.reader(fh, strict=True) )
        cols = [ ColumnHeader(*c).csv for c in columns ] \
            if csvnames else [ c[0] for c in columns ]
        if cols[0]!='TIMESTAMP':
            raise Toa5Error("Can't (yet) handle files where the first column isn't TIMESTAMP")
        dframe = pandas.read_csv(fh, header=None, names=cols,
            parse_dates=[0], index_col=[0], na_values=["NAN"], low_memory=False)
        dframe.attrs['columns'] = columns
        dframe.attrs['toa5_envline'] = envline
        return dframe
