#!/usr/bin/env python3
"""Metadata for representing datalogger data tables.

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
import re
import json
import pkgutil
import warnings
from dataclasses import dataclass, field, fields
from itertools import chain, combinations
from enum import Enum
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo
from typing import Self, NamedTuple, Optional
from collections.abc import Sequence, Callable
from more_itertools import unique_everseen
from igbpyutils.iter import no_duplicates
from jsonvalidate import load_json_schema, validate_json, freeze_json
import datatypes
from functools import cache
from dateutil.relativedelta import relativedelta

short_units :dict[str,str] = json.loads(pkgutil.get_data('loggerdata', 'short_units.json').decode('UTF-8'))
del short_units['$comment']

class Interval(Enum):
    UNDEF = 0
    MIN15 = 1
    MIN30 = 2
    HOUR1 = 3
    DAY1 = 4
    WEEK1 = 5
    MONTH1 = 6
    @property
    @cache
    def delta(self) -> timedelta|relativedelta:
        match self:
            case Interval.MIN15:  return timedelta(minutes=15)
            case Interval.MIN30:  return timedelta(minutes=30)
            case Interval.HOUR1:  return timedelta(hours=1)
            case Interval.DAY1:   return timedelta(days=1)
            case Interval.WEEK1:  return timedelta(weeks=1)
            case Interval.MONTH1: return relativedelta(months=1)
            case _: raise ValueError(f"unhandled interval {self!r}")
    @property
    @cache
    def floor(self) -> Callable[[datetime], datetime]:
        match self:
            case Interval.MIN15:
                def timefloor(stamp :datetime) -> datetime:
                    if stamp.minute >= 45: cmin = 45
                    elif stamp.minute >= 30: cmin = 30
                    elif stamp.minute >= 15: cmin = 15
                    else: cmin = 0
                    return stamp.replace(minute=cmin, second=0, microsecond=0)
            case Interval.MIN30:
                def timefloor(stamp :datetime) -> datetime:
                    if stamp.minute>=30: cmin = 30
                    else: cmin = 0
                    return stamp.replace(minute=cmin, second=0, microsecond=0)
            case Interval.HOUR1:
                def timefloor(stamp :datetime) -> datetime:
                    return stamp.replace(minute=0, second=0, microsecond=0)
            case Interval.DAY1:
                def timefloor(stamp :datetime) -> datetime:
                    return stamp.replace(hour=0, minute=0, second=0, microsecond=0)
            case Interval.WEEK1:
                def timefloor(stamp :datetime) -> datetime:
                    isoyear, isoweek, _isoday = stamp.isocalendar()
                    newdate = datetime.fromisocalendar(isoyear, isoweek, 1)
                    return stamp.replace(year=newdate.year, month=newdate.month, day=newdate.day,
                                         hour=0, minute=0, second=0, microsecond=0)
            case Interval.MONTH1:
                def timefloor(stamp :datetime) -> datetime:
                    return stamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            case _: raise ValueError(f"unhandled interval {self!r}")
        return timefloor

class LoggerOrigDataType(Enum):
    CB_FP2 = 0
    CB_IEEE4 = 1  # aka Float
    # Note that the Campbell manuals don't actually specify what the internal type of the following are. Maybe Long?
    CB_Timestamp = 2
    CB_Integer = 3

class ColumnHeader(NamedTuple):
    """Class (named tuple) representing a column header.

    This class represents a column header as it would be read from a CSV file,
    so when its fields are empty, this is represented by empty strings, not
    by ``None``, as it is done in ``MdBaseCol``.

    The ``prc`` field comes from the Campbell TOA5 format and is defined as
    the "data process used to produce the field of data", e.g. "Avg", "Max", etc.
    """
    name :str
    unit :str = ""
    prc :str = ""
    @property
    def csv(self) -> str:
        csv = self.name
        if self.prc is not None and len(self.prc) and not self.name.endswith(self.prc):
            csv += "/" + self.prc
        # the "TIMESTAMP" and "RECORD" columns from Campbell loggers don't need unit speifications
        if self.unit is not None and len(self.unit) and \
                not ( self.name=='TIMESTAMP' and self.unit=='TS' or self.name=='RECORD' and self.unit=='RN' ) \
                and len(short_units.get(self.unit, self.unit)):
            csv += "[" + short_units.get(self.unit, self.unit) + "]"
        return csv

class MdBase:
    """Base class for metadata classes."""
    @classmethod
    def from_dict(cls :type, d :dict):
        """Convert a dict to an object of this class."""
        # noinspection PyDataclass
        return cls(**{ f.name: d[f.name] if f.name in d else None for f in fields(cls) })
    def validate(self) -> Self:  # implementations must "return self"!
        """Validate this object, throwing errors if problems are found."""
        # Possible To-Do for Later: type checking on metadata classes (e.g. pydantic)
        raise NotImplementedError()  # pragma: no cover
    # utility function for subclasses
    _ident_re = re.compile(r'\A[A-Za-z_][A-Za-z_0-9]{1,254}\Z')
    @staticmethod
    def _valid_ident(s :str):
        """Test whether the input is a valid identifier; raise an exception otherwise."""
        if not MdBase._ident_re.fullmatch(s):
            raise ValueError(f"not a valid identifier: {s!r}")

@dataclass(kw_only=True)
class MdBaseCol(MdBase):
    """A basic column definition."""
    name: str
    unit: Optional[str] = None
    prc:  Optional[str] = None
    @property
    def hdr(self) -> ColumnHeader:
        return ColumnHeader(name=self.name, unit="" if self.unit is None else self.unit, prc="" if self.prc is None else self.prc)
    _sqlcolname_re = re.compile(r'\((\d+)\)\Z')
    @property
    def sql(self) -> str:
        return self._sqlcolname_re.sub( lambda m: "_"+m.group(1), self.name ).lower()
    def __post_init__(self): pass  # just here so it can be overridden
    # the parens will be turned to underscores so 3 digits + underscore is 4 chars, therefore 250 other chars
    # Possible To-Do for Later: Column names such as "Values(2,1)" are theoretically also possible.
    _colname_re = re.compile(r'\A[A-Za-z_][A-Za-z_0-9]{1,250}(?:\(\d{1,3}\))?\Z')
    # Generating a regex character class for printable ASCII that can then be customized:
    # print( "r'''[" + bytes(range(0x20, 0x7F)).decode("ASCII") \
    #   .replace("\\","\\\\").replace("-","\\-").replace("]","\\]") \
    #   .replace(bytes(range(ord('A'),ord('Z')+1)).decode('ASCII'),"A-Z") \
    #   .replace(bytes(range(ord('a'),ord('z')+1)).decode('ASCII'),"a-z") \
    #   .replace(bytes(range(ord('0'),ord('9')+1)).decode('ASCII'),"0-9") + "]'''" )
    # => r'''[ !"#$%&'()*+,\-./0-9:;<=>?@A-Z[\\\]^_`a-z{|}~]'''
    # Possible To-Do for Later: Limit allowed characters in units more?
    # don't allow backslashes or square brackets in units (length limit is based on experience):
    _unit_re = re.compile(r'''\A[ !"#$%&'()*+,\-./0-9:;<=>?@A-Z^_`a-z{|}~]{0,64}\Z''')
    # we'll limit process identifiers pretty strictly for now, as the Campbell manuals seem to say this is fine:
    _prc_re = re.compile(r'''\A[A-Za-z_0-9\- .]{0,32}\Z''')
    def validate(self):
        if not self._colname_re.fullmatch(self.name):
            raise ValueError(f"invalid column name {self.name!r}")
        if self.unit is not None and not self._unit_re.fullmatch(self.unit):
            raise ValueError(f"invalid unit {self.unit!r} on column {self.name}")
        if self.prc is not None and not self._prc_re.fullmatch(self.prc):
            raise ValueError(f"invalid prc {self.prc!r} on column {self.name}")
        return self

@dataclass(kw_only=True)
class MdColumn(MdBaseCol):
    """A full column definition."""
    type:    Optional[datatypes.BaseType] = None  #TODO Later: won't be optional in the future (once all our logger metadata is complete)
    lodt:    Optional[LoggerOrigDataType] = None
    var:     Optional[str] = None
    desc:    Optional[str] = None
    plotgrp: Optional[str] = None
    sens:    Optional[str] = None
    def __post_init__(self):
        super().__post_init__()
        if self.type is not None and not isinstance(self.type, datatypes.BaseType):
            # noinspection PyTypeChecker
            self.type = datatypes.from_string(self.type)  # raises error on failed parse
    def validate(self):
        if self.lodt is not None and not isinstance(self.lodt, LoggerOrigDataType):
            raise ValueError(f"not a LoggerOriginalDataType: {self.lodt!r}")
        return super().validate()

class MappingType(Enum):
    VIEW = 1

@dataclass(kw_only=True)
class MdMapEntry(MdBase):
    """An entry in a ``MdMapping``."""
    old: MdBaseCol
    new: MdBaseCol
    def validate(self):
        self.old.validate()
        self.new.validate()
        return self

@dataclass(kw_only=True)
class MdMapping(MdBase):
    """A mapping from certain columns to other columns."""
    name :str
    type: MappingType
    map:  list[MdMapEntry]
    @property
    def sql(self):
        return self.name.lower()
    def validate(self):
        self._valid_ident(self.name)
        for m in self.map: m.validate()
        return self

@dataclass(kw_only=True)
class MdTable(MdBase):
    """A class representing a table definition.

    ``variants`` contains the "Variant Maps" for this table's columns.
    Variant maps are dicts where the keys are tuples of ``ColumnHeader`` tuples,
    so that when loading a logger data file, it can easily be
    looked up which variant the file is. The value for each key is a
    tuple of which column index in the final table the column from that
    data file should be assigned.
    """
    name: str
    prikey: int  # is guessed to be 0 for TOA5 files where the first column is TIMESTAMP (in code below)
    interval: Interval
    columns:  list[MdColumn]
    variants: dict[ tuple[ColumnHeader, ...], tuple[int, ...] ]
    mappings: dict[str, MdMapping] = field(default_factory=dict)
    parent: 'Metadata' = field(default=None, init=False, repr=False, compare=False)  # is set in Metadata.__post_init__()
    @property
    def sql(self):
        return ( self.parent.logger_name + "_" + self.name ).lower()
    @property
    def tblident(self):
        return self.parent.logger_name+"/"+self.name
    def validate(self):
        if not isinstance(self.parent, Metadata):
            raise TypeError(repr(self.parent))
        if self not in self.parent.tables.values():
            raise ValueError(f"table {self.sql} not in {self.parent!r}")
        if not 0 <= self.prikey < len(self.columns):
            raise IndexError("prikey outside of range")
        for c in self.columns: c.validate()
        for mn, mm in self.mappings.items():
            self._valid_ident(mn)
            mm.validate()
        return self

@dataclass(kw_only=True)
class Toa5EnvMatch(MdBase):
    """A class representing values to be matched against a TOA5 "environment line"."""
    station_name:  Optional[str] = None
    logger_model:  Optional[str] = None
    logger_serial: Optional[str] = None
    logger_os:     Optional[str] = None
    program_name:  Optional[str] = None
    program_sig:   Optional[str] = None
    def validate(self):
        if all( getattr(self, f.name) is None for f in fields(self)):
            raise ValueError("all fields of Toa5EnvMatch are None")
        return self

class LoggerType(Enum):
    TOA5 = 1

class TimeRange(NamedTuple):
    """Represents either a time range or a timestamp (when ``end`` is ``None``)."""
    why :str
    start :datetime
    end :Optional[datetime] = None
    def validate(self):
        if not self.why or self.why.isspace():
            raise ValueError('range "why" is empty')
        if self.end and self.end <= self.start:
            raise ValueError(f"range end <= start ({self!r})")
    @staticmethod
    def validate_set(ranges :Sequence['TimeRange']):
        for x, y in combinations(ranges, 2):
            if x.end and y.end:  # two ranges
                # To-Do for Later: I think this isn't the most efficient set of checks
                # x---x or  x-x  or x---x   or   x---x
                #  y-y     y---y      y---y    y---y
                bad = x.start < y.start < x.end and x.start < y.end < x.end \
                      or y.start < x.start < y.end and y.start < x.end < y.end \
                      or x.start < y.start < x.end or x.start < y.end < x.end
            elif x.end:  # x is a range, y is not
                bad = x.start < y.start < x.end
            elif y.end:  # y is a range, x is not
                bad = y.start < x.start < y.end
            else:  # two timestamps
                bad = x.start == y.start
            if bad:
                raise ValueError(f"overlapping ranges in a set: {x=} {y=}")

@dataclass(kw_only=True)
class Metadata(MdBase):
    """The main class representing logger metadata."""
    logger_name: str
    tables: dict[str, MdTable]
    logger_type :LoggerType
    toa5_env_match: Optional[Toa5EnvMatch] = None
    tz: Optional[tzinfo] = None
    min_datetime: Optional[datetime] = None
    variants: Optional[Sequence[str]] = None
    sensors: Optional[dict[str,str]] = None
    known_gaps :tuple[TimeRange, ...] = ()
    skip_recs :tuple[TimeRange, ...] = ()
    def __post_init__(self):
        for tbl in self.tables.values():
            tbl.parent = self
    def validate(self):
        self._valid_ident(self.logger_name)
        match self.logger_type:
            case LoggerType.TOA5:
                if self.toa5_env_match is None:
                    raise ValueError("toa5_env_match not set")
                self.toa5_env_match.validate()
            case _:
                raise ValueError(f"invalid {self.logger_type=}")
        if self.variants is not None:
            if not self.variants: raise ValueError("empty variants (should be None)")
            for v in self.variants: self._valid_ident(v)
        if self.sensors is not None:
            if not self.sensors: raise ValueError("empty sensors (should be None)")
            for sid, sn in self.sensors.items():
                self._valid_ident(sid)
                if len(sn.strip())<1:
                    raise ValueError(f"Sensor id {sid!r} has an empty value")
        for e in chain(self.known_gaps, self.skip_recs):
            if not e.start.tzinfo and not self.tz:
                raise ValueError(f"No TZ for time range start ({e!r})")
            if e.end and not e.end.tzinfo and not self.tz:
                raise ValueError(f"No TZ for time range end ({e!r})")
            e.validate()
        TimeRange.validate_set(self.known_gaps)
        TimeRange.validate_set(self.skip_recs)
        for tn, tt in self.tables.items():
            self._valid_ident(tn)
            if tt.parent is not self:
                raise ValueError(f"table {tn} doesn't have me as its parent")
            tt.validate()
            if tt.name != tn:
                raise ValueError(f"table key {tn!r} != name {tt.name!r}")
            have_ts_no_tz = False
            have_ts_with_tz = False
            for c in tt.columns:
                if isinstance(c.type, datatypes.TimestampNoTz): have_ts_no_tz = True
                if isinstance(c.type, datatypes.TimestampWithTz): have_ts_with_tz = True
                if c.var is not None and ( self.variants is None or c.var not in self.variants ):
                    raise RuntimeError(f"invalid variant {c.var!r} on column {c.name}")
            if have_ts_no_tz and have_ts_with_tz:
                warnings.warn(f"Table {tn} has mixed TimestampNoTz/WithTz types")
            if not self.tz:
                if have_ts_no_tz: raise ValueError(f"Table {tn} has TimestampNoTz columns but there is no TZ set")
                else: warnings.warn(f"Logger doesn't have a TZ set")
            else:
                try:
                    tzname = self.tz.tzname(None)
                except Exception as ex:
                    raise ValueError(f"Failed to get tzname from {self.tz}") from ex
                if tzname!='UTC' and have_ts_no_tz:
                    warnings.warn(f"Table {tn} has TimestampNoTz columns and non-UTC timezone (converstion to UTC recommended!)")
            # the dupe check on hdr covers the combination of name/unit/prc
            seen_hdr = set(no_duplicates( (c.hdr for c in tt.columns), name='column') )
            set(no_duplicates( (c.sql for c in tt.columns), name='sql column name'))
            set(no_duplicates( (c.hdr.csv for c in tt.columns), name='csv column name'))
            for mn, mm in tt.mappings.items():
                if mn != mm.name:
                    raise RuntimeError(f"mapping key {mn!r} != name {mm.name!r}")
                for m in mm.map:
                    if m.old.hdr not in seen_hdr:
                        raise RuntimeError(f"map {mn} 'old' specifies unknown column {m.old!r}")
                    if m.new.hdr in seen_hdr:
                        raise RuntimeError(f"map {mn} 'new' specifies existing column {m.new!r}")
                set(no_duplicates( (m.new.hdr for m in mm.map), name="mapping target"))
        return self

class MdCollection(Sequence[Metadata]):
    """A collection of ``Metadata``s that also allows easy access to the tables contained therein."""
    def __init__(self, *anymd :Metadata|MdTable|Self|str):
        # first, parse out the arguments
        self._mds = tuple( unique_everseen( a for a in anymd if isinstance(a, Metadata) ) )
        tables = [ a for a in anymd if not isinstance(a, Metadata | MdCollection) ]
        # noinspection PyUnresolvedReferences
        tables.extend(chain.from_iterable( a.tables for a in anymd if isinstance(a, MdCollection) ))
        # if no tables were provided, populate them from the metadatas
        if not tables:
            if not self._mds: raise ValueError(f"no metadatas or tables given")
            tables = list( chain.from_iterable( md.tables.values() for md in self._mds ) )
        # double-check that we now have tables
        if not tables: raise ValueError(f"no tables")
        # if no metadatas were provided, populate them from the tables
        if len(self._mds)<1:
            self._mds = tuple( unique_everseen( tb.parent for tb in tables if isinstance(tb, MdTable) ) )
            if not self._mds: raise ValueError(f"no metadatas could be determined from tables")
        # => now we have metadatas and tables
        # check logger names for uniqueness
        set(no_duplicates( (m.logger_name for m in self._mds), name="logger name" ))
        # resolve and check tables
        for i, tbl in enumerate(tables):
            if isinstance(tbl, MdTable):
                if tbl.parent not in self._mds:
                    raise ValueError(f"table is not in metadatas: {tbl.name!r}")
            else:  # assume str, find table by name
                found = [ t for md in self._mds for t in md.tables.values() if t.name == tbl ]
                if len(found)>1:
                    raise ValueError(f"table name {tbl!r} appears more than once in metadatas")
                elif len(found)<1:
                    raise ValueError(f"table name {tbl!r} not found in metadatas")
                else:  # len(found)==1
                    tables[i] = found[0]
        self.tables = tuple( unique_everseen( tables ) )
    def __contains__(self, item):
        if isinstance(item, MdTable): return item in self.tables
        return item in self._mds
    def __iter__(self): return iter(self._mds)
    def __reversed__(self): return reversed(self._mds)
    def __len__(self): return len(self._mds)
    def __getitem__(self, key): return self._mds[key]
    def __eq__(self, other):
        if isinstance(other, MdCollection):
            return self._mds == other._mds and self.tables == other.tables
        else: return super().__eq__(other)

_logger_metadata_schema = load_json_schema( pkgutil.get_data('loggerdata', 'metadata.schema.json') )
_tzoffset_re = re.compile(r'([+-])(\d\d):(\d\d)')

def load_logger_metadata(file) -> Metadata:
    """Reads a JSON metadata definition from a file and validates it."""
    js = validate_json(_logger_metadata_schema, file)
    if js is None: raise RuntimeError(f"File {file!r} failed to validate")
    js = freeze_json(js)
    md = {
        'logger_name': js['logger_name'],
        'tables': {} }
    if 'toa5_env_match' in js:
        md['toa5_env_match'] = Toa5EnvMatch.from_dict(js['toa5_env_match'])
        md['logger_type'] = LoggerType.TOA5
    else:  # pragma: no cover
        pass  # this currently shouldn't happen b/c the JSON schema requires the field
    # check variants
    unused_variants = set()
    if 'variants' in js:
        set(no_duplicates(js['variants'], name='variant'))
        md['variants'] = js['variants']
        #TODO Later: the first variant doesn't need to be referenced iff the others are referenced
        unused_variants = set(md['variants'][1:])
    unused_sensors = set()
    if 'sensors' in js:
        set(no_duplicates(js['sensors'].values(), name='sensor'))
        md['sensors'] = dict(**js['sensors'])
        unused_sensors = set(md['sensors'].keys())
    # check tz and min_datetime
    if 'tz' in js:
        if m := _tzoffset_re.fullmatch(js['tz']):
            # e.g. "-04:30" becomes datetime.timezone(datetime.timedelta(days=-1, seconds=70200))
            # >>> from datetime import datetime, timezone, timedelta
            # >>> datetime.fromisoformat('2021-03-04 12:34:56-04:30')
            # >>> datetime.strptime('2021-03-04 12:34:56', '%Y-%m-%d %H:%M:%S').replace( tzinfo=timezone(timedelta(days=-1, seconds=70200)) )
            delta = timedelta(hours=int(m.group(2)), minutes=int(m.group(3)))
            if m.group(1) == '-': delta = -delta
            md['tz'] = timezone(delta)
        else:
            md['tz'] = ZoneInfo(js['tz'])  # will raise exception if not found
    else: pass  # the case of tz not being set is handled in validate()
    if 'min_datetime' in js:
        md['min_datetime'] = datetime.fromisoformat(js['min_datetime'])
        if md['min_datetime'].tzinfo is None and 'tz' in md:
            md['min_datetime'] = md['min_datetime'].replace( tzinfo = md['tz'] )
    for k in ('known_gaps','skip_records'):
        if k in js:
            md['skip_recs' if k=='skip_records' else k] = tuple(
                TimeRange( why=el['why'], start=datetime.fromisoformat(el['time']),
                end=datetime.fromisoformat(el['end'] ) if 'end' in el else None) for el in js[k] )
    # handle tables and columns
    for table, tdata in js['tables'].items():
        tmd = {
            "name" : table,
            "columns": [ MdColumn.from_dict(c) for c in tdata['columns'] ],
            "variants": {},
            "mappings": {},
        }
        # process variants into variant maps
        tempvar = {}  # "temporary variant map", will be distilled below
        firstvariant = None
        if 'variants' in js:
            for v in js['variants']: tempvar[v] = { "k": [], "i": [] }
            firstvariant = js['variants'][0]
        if not tempvar:  # need at least one for loop below
            tempvar[None] = { "k": [], "i": [] }
        tbl_vars = set()  # which variants are actually used in this table
        for i, col in enumerate(tmd['columns']):
            if col.lodt is not None:
                match col.lodt:
                    case 'FP2':   col.lodt = LoggerOrigDataType.CB_FP2
                    case 'IEEE4': col.lodt = LoggerOrigDataType.CB_IEEE4
                    case 'TS':    col.lodt = LoggerOrigDataType.CB_Timestamp
                    case 'Int':   col.lodt = LoggerOrigDataType.CB_Integer
                    # this shouldn't happen because it's validated by the schema
                    case _: raise ValueError(f"column {col.name} invalid lodt {col.lodt!r}")  # pragma: no cover
            if col.sens is not None:
                if 'sensors' not in md or col.sens not in md['sensors']:
                    raise ValueError(f"column {col.name} references unknown sensor {col.sens}")
                unused_sensors.discard(col.sens)
            if col.var is not None:  # this column is only part of this variant
                tbl_vars.add( var := col.var )
                unused_variants.discard(col.var)
            else: var = None  # this column is part of all variants
            for vn, v in tempvar.items():
                if var is None or var == vn:
                    v['k'].append( col.hdr )
                    v['i'].append( i )
        if 'prikey' in tdata:
            tmd['prikey'] = tdata['prikey']
        elif 'toa5_env_match' in js and tmd['columns'][0].hdr == ('TIMESTAMP','TS',''):
            tmd['prikey'] = 0
        else:
            raise ValueError(f"table {table} doesn't define a prikey and we couldn't guess one")
        if 'interval' in tdata:
            match tdata['interval']:
                case '15min': tmd['interval'] = Interval.MIN15
                case '30min': tmd['interval'] = Interval.MIN30
                case '1hour': tmd['interval'] = Interval.HOUR1
                case '1day': tmd['interval'] = Interval.DAY1
                case '1week': tmd['interval'] = Interval.WEEK1
                case '1month': tmd['interval'] = Interval.MONTH1
                # this shouldn't happen because it's validated by the schema
                case _: raise ValueError(f"Invalid interval {tdata['interval']!r}")  # pragma: no cover
        else: tmd['interval'] = Interval.UNDEF
        if tbl_vars:
            # The first variant in the list gets special treatment: It is always a possible variant,
            # the others are only included if they are seen in the columns.
            if firstvariant is not None: tbl_vars.add(firstvariant)
            for s in ( jv for jv in js['variants'] if jv in tbl_vars ):  # keep same order as in json
                tmd['variants'][tuple(tempvar[s]['k'])] = tuple(tempvar[s]['i'])
            # Lastly, generate a variant that consists of all columns from the metadata.
            # This is important for re-importing previously exported files.
            tmd['variants'][tuple( col.hdr for col in tmd['columns'] )] = tuple(range(len(tmd['columns'])))
        else:  # no variants seen for this table, so they should all be identical
            v = next(iter(tempvar.values()))
            tmd['variants'][tuple(v['k'])] = tuple(v['i'])
        set(no_duplicates(tmd['variants'].values(), name='variant value'))  # sanity check, should hopefully never happen, otherwise it's a programming error
        # handle mappings
        if 'mappings' in tdata:
            for mname, mval in tdata['mappings'].items():
                if mval['type'] != 'view':  # pragma: no cover
                    raise RuntimeError(f"map {mname} unsupported type")  # shouldn't happen b/c JSON Schema checks this
                tmd['mappings'][mname] = MdMapping( name=mname, type=MappingType.VIEW,
                    map=[ MdMapEntry( old=MdBaseCol.from_dict(m['old']), new=MdBaseCol.from_dict(m['new']) ) for m in mval['map'] ] )
        md['tables'][table] = MdTable(**tmd)
    if unused_sensors:
        raise ValueError(f"The following sensors were never referenced: {unused_sensors!r}")
    if unused_variants:
        raise ValueError(f"The following variants were never referenced: {unused_variants!r}")
    return Metadata(**md).validate()

if __name__ == '__main__':  # pragma: no cover
    import sys
    import argparse
    from pprint import pprint
    from igbpyutils.file import autoglob
    parser = argparse.ArgumentParser(description='Logger Metadata Handler')
    parser.add_argument('-d', '--dump', help="dump loaded metadata", action="store_true")
    parser.add_argument('jsons', help="", nargs="+")
    args = parser.parse_args()
    for j in autoglob(args.jsons):
        metad = load_logger_metadata(j)
        if args.dump: pprint(metad)
    sys.exit(0)
