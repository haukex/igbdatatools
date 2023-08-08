#!/usr/bin/env python3
"""Tests for loggerdata.metadata.

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
import unittest
from pathlib import Path
from loggerdata.metadata import DataInterval, load_logger_metadata, MdBaseCol, MdColumn, MdMapEntry, MdMapping, MappingType, \
    MdTable, Toa5EnvMatch, Metadata, LoggerType, ColumnHeader, MdCollection, LoggerOrigDataType, TimeRange, MdKnownIssue, \
    KnownIssueType
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from datatypes import TimestampNoTz, NonNegInt, Num
from igbpyutils.test import tempcopy

_TestLogger_md = Metadata(
    logger_name = "TestLogger",
    logger_type = LoggerType.TOA5,
    toa5_env_match = Toa5EnvMatch(
        logger_model  = "CR1000X",
        logger_serial = "12342",
        station_name  = "TestLogger",
    ),
    tz = ZoneInfo("UTC"),
    min_datetime = datetime(2021,6,18,11,0,0, tzinfo=ZoneInfo("UTC")),  # "2021-06-18 11:00:00"
    variants = ("abc", "def"),
    sensors = {
        "acme42": "Acme Pressure and Humidity Sensor #42",
        "acme532": "Acme Model 532 Air Temperature Sensor",
    },
    known_gaps = (
        TimeRange(why="example missing record", start=datetime.fromisoformat("2021-06-19 13:00:00Z")),
        TimeRange(why="example gap", start=datetime.fromisoformat("2021-06-19 15:00:00Z"), end=datetime.fromisoformat("2021-06-19 17:00:00Z")),
    ),
    skip_recs = (
        TimeRange(why="example bad record (duplicate TS with differing data)", start=datetime.fromisoformat("2021-06-19 19:00:00Z")),
    ),
    ignore_tables = frozenset(( 'Hello', 'World' )),
    tables = {
        "Daily": MdTable(
            name = "Daily",
            prikey = 0,
            interval = DataInterval.DAY1,
            columns = [
                MdColumn( name="TIMESTAMP",   unit="TS",               type=TimestampNoTz(),     lodt=LoggerOrigDataType.CB_Timestamp ),
                MdColumn( name="RECORD",      unit="RN",               type=NonNegInt(),         lodt=LoggerOrigDataType.CB_Integer   ),
                MdColumn( name="BattV_Min",   unit="Volts", prc="Min", type=Num(4,2),            lodt=LoggerOrigDataType.CB_IEEE4     ),
                MdColumn( name="BattV_TMn",                 prc="TMn", type=TimestampNoTz(),     lodt=LoggerOrigDataType.CB_Timestamp ),
                MdColumn( name="PTemp_C_Min", unit="Deg C", prc="Min", type=Num(5,2),            lodt=LoggerOrigDataType.CB_FP2,      plotgrp="PTemp", desc= "Panel Temperature Minimum", ),
                MdColumn( name="PTemp_C_TMn",               prc="TMn", type=TimestampNoTz(),     lodt=LoggerOrigDataType.CB_Timestamp ),
                MdColumn( name="PTemp_C_Max", unit="Deg C", prc="Max", type=Num(5,2),            lodt=LoggerOrigDataType.CB_FP2,      plotgrp="PTemp"),
                MdColumn( name="PTemp_C_TMx",               prc="TMx", type=TimestampNoTz(),     lodt=LoggerOrigDataType.CB_Timestamp ),
            ],
            known_issues = [
                MdKnownIssue( type=KnownIssueType.BAD, cols=("PTemp_C_Min",),
                              when=TimeRange( start=datetime(2021,6,22,tzinfo=timezone.utc), why="example" ) )
            ],
            variants = {
                (ColumnHeader("TIMESTAMP", "TS", ""), ColumnHeader("RECORD", "RN", ""), ColumnHeader("BattV_Min", "Volts", "Min"),
                 ColumnHeader("BattV_TMn", "", "TMn"), ColumnHeader("PTemp_C_Min", "Deg C", "Min"), ColumnHeader("PTemp_C_TMn", "", "TMn"),
                 ColumnHeader("PTemp_C_Max", "Deg C", "Max"), ColumnHeader("PTemp_C_TMx", "", "TMx")): (0, 1, 2, 3, 4, 5, 6, 7)
            }
        ),
        "Hourly": MdTable(
            name = "Hourly",
            prikey = 0,
            interval = DataInterval.HOUR1,
            columns = [
                MdColumn( name="TIMESTAMP",   unit="TS",               type=TimestampNoTz(),     ),
                MdColumn( name="RECORD",      unit="RN",               type=NonNegInt(),         ),
                MdColumn( name="BattV_Min",   unit="Volts", prc="Min", type=Num(4,2),            ),
                MdColumn( name="PTemp_C_Min", unit="Deg C", prc="Min", type=Num(5,2),            plotgrp="PTemp"),
                MdColumn( name="PTemp_C_Max", unit="Deg C", prc="Max", type=Num(5,2),            plotgrp="PTemp"),
                MdColumn( name="AirT_C(42)",  unit="Deg C", prc="Smp", type=Num(5,2), var="abc", sens="acme532", desc= "air temperature single sample only", ),
                MdColumn( name="AirT_C_Avg",  unit="Deg C", prc="Avg", type=Num(5,2), var="def", sens="acme532", desc= "air temperature average over sampling period", ),
                MdColumn( name="RelHumid",    unit="%",     prc="Smp", type=Num(5,2),            sens="acme42"),
                MdColumn( name="BP_mbar_Avg", unit="mbar",  prc="Avg", type=Num(7,3), var="def", sens="acme42"),
            ],
            variants = {
                ( ColumnHeader("TIMESTAMP", "TS", ""), ColumnHeader("RECORD", "RN", ""), ColumnHeader("BattV_Min", "Volts", "Min"),
                  ColumnHeader("PTemp_C_Min", "Deg C", "Min"), ColumnHeader("PTemp_C_Max", "Deg C", "Max"),
                  ColumnHeader("AirT_C(42)", "Deg C", "Smp"), ColumnHeader("RelHumid", "%", "Smp") ) : (0, 1, 2, 3, 4, 5, 7),
                ( ColumnHeader("TIMESTAMP", "TS", ""), ColumnHeader("RECORD", "RN", ""), ColumnHeader("BattV_Min", "Volts", "Min"),
                  ColumnHeader("PTemp_C_Min", "Deg C", "Min"), ColumnHeader("PTemp_C_Max", "Deg C", "Max"), ColumnHeader("AirT_C_Avg", "Deg C", "Avg"),
                  ColumnHeader("RelHumid", "%", "Smp"), ColumnHeader("BP_mbar_Avg", "mbar", "Avg") ) : (0, 1, 2, 3, 4, 6, 7, 8),
                ( ColumnHeader("TIMESTAMP", "TS", ""), ColumnHeader("RECORD", "RN", ""), ColumnHeader("BattV_Min", "Volts", "Min"),
                  ColumnHeader("PTemp_C_Min", "Deg C", "Min"), ColumnHeader("PTemp_C_Max", "Deg C", "Max"), ColumnHeader("AirT_C(42)", "Deg C", "Smp"),
                  ColumnHeader("AirT_C_Avg", "Deg C", "Avg"), ColumnHeader("RelHumid", "%", "Smp"), ColumnHeader("BP_mbar_Avg", "mbar", "Avg") ) : (0, 1, 2, 3, 4, 5, 6, 7, 8),
            },
            mappings = {
                "Press_Humid": MdMapping(
                    name ="Press_Humid",
                    type = MappingType.VIEW,
                    map  = [
                        MdMapEntry(
                            old = MdBaseCol( name="TIMESTAMP",   unit="TS"               ),
                            new = MdBaseCol( name="Timestamp",                           ),
                        ),
                        MdMapEntry(
                            old = MdBaseCol( name="BP_mbar_Avg", unit="mbar",  prc="Avg" ),
                            new = MdBaseCol( name="BPress_Avg",  unit="mbar",  prc="Avg" ),
                        ),
                        MdMapEntry(
                            old = MdBaseCol( name="RelHumid",    unit="%",     prc="Smp" ),
                            new = MdBaseCol( name="RH_Smp",      unit="%",     prc="Smp" ),
                        ),
                    ]
                )
            }
        )
    }
).validate()
_TestLogger_props :dict[str, tuple[dict, ...]] = {
    "Daily": (
        dict( hdr=ColumnHeader("TIMESTAMP", "TS"),             sql="timestamp",   csv="TIMESTAMP",          ),
        dict( hdr=ColumnHeader("RECORD", "RN"),                sql="record",      csv="RECORD",             ),
        dict( hdr=ColumnHeader("BattV_Min", "Volts", "Min"),   sql="battv_min",   csv="BattV_Min[V]",       ),
        dict( hdr=ColumnHeader("BattV_TMn", "", "TMn"),        sql="battv_tmn",   csv="BattV_TMn",          ),
        dict( hdr=ColumnHeader("PTemp_C_Min", "Deg C", "Min"), sql="ptemp_c_min", csv="PTemp_C_Min[°C]",    ),
        dict( hdr=ColumnHeader("PTemp_C_TMn", "", "TMn"),      sql="ptemp_c_tmn", csv="PTemp_C_TMn",        ),
        dict( hdr=ColumnHeader("PTemp_C_Max", "Deg C", "Max"), sql="ptemp_c_max", csv="PTemp_C_Max[°C]",    ),
        dict( hdr=ColumnHeader("PTemp_C_TMx", "", "TMx"),      sql="ptemp_c_tmx", csv="PTemp_C_TMx",        ),
    ),
    "Hourly": (
        dict( hdr=ColumnHeader("TIMESTAMP", "TS"),             sql="timestamp",   csv="TIMESTAMP",          ),
        dict( hdr=ColumnHeader("RECORD", "RN"),                sql="record",      csv="RECORD",             ),
        dict( hdr=ColumnHeader("BattV_Min", "Volts", "Min"),   sql="battv_min",   csv="BattV_Min[V]",       ),
        dict( hdr=ColumnHeader("PTemp_C_Min", "Deg C", "Min"), sql="ptemp_c_min", csv="PTemp_C_Min[°C]",    ),
        dict( hdr=ColumnHeader("PTemp_C_Max", "Deg C", "Max"), sql="ptemp_c_max", csv="PTemp_C_Max[°C]",    ),
        dict( hdr=ColumnHeader("AirT_C(42)", "Deg C", "Smp"),  sql="airt_c_42",   csv="AirT_C(42)/Smp[°C]", ),
        dict( hdr=ColumnHeader("AirT_C_Avg", "Deg C", "Avg"),  sql="airt_c_avg",  csv="AirT_C_Avg[°C]",     ),
        dict( hdr=ColumnHeader("RelHumid", "%", "Smp"),        sql="relhumid",    csv="RelHumid/Smp[%]",    ),
        dict( hdr=ColumnHeader("BP_mbar_Avg", "mbar", "Avg"),  sql="bp_mbar_avg", csv="BP_mbar_Avg[mbar]",  ),
    ),
}

_DummyLogger_md = Metadata(
    logger_name = "DummyLogger",
    logger_type = LoggerType.TOA5,
    toa5_env_match = Toa5EnvMatch(
        logger_serial = "111",
    ),
    tz = ZoneInfo("UTC"),
    tables = {
        "Daily": MdTable(
            name = "Daily",
            prikey = 0,
            interval = DataInterval.UNDEF,
            columns = [
                MdColumn( name="TIMESTAMP", unit="TS", type=TimestampNoTz() ),
            ],
            variants = {
                (ColumnHeader("TIMESTAMP", "TS", ""),): (0,)
            },
        )
    }
).validate()

class TestLoggerMetadata(unittest.TestCase):

    def test_interval_as_timedelta(self):
        with self.assertRaises(ValueError): _ = DataInterval.UNDEF.delta
        self.assertEqual(DataInterval.MIN15.delta,  timedelta(minutes=15))
        self.assertEqual(DataInterval.MIN30.delta,  timedelta(minutes=30))
        self.assertEqual(DataInterval.HOUR1.delta,  timedelta(hours=1))
        self.assertEqual(DataInterval.DAY1.delta,   timedelta(days=1))
        self.assertEqual(DataInterval.WEEK1.delta,  timedelta(weeks=1))
        self.assertEqual(DataInterval.MONTH1.delta, relativedelta(months=1))

    def test_timefloor(self):
        with self.assertRaises(ValueError): _ = DataInterval.UNDEF.floor
        self.assertEqual( DataInterval.MIN15.floor(datetime(2023,6,23,10,59,59)), datetime(2023,6,23,10,45,0,0) )
        tf_15m = DataInterval.MIN15.floor
        self.assertEqual( tf_15m(datetime(2023,3,10,10,55,23,4523)), datetime(2023, 3,10,10,45,0,0) )
        self.assertEqual( tf_15m(datetime(2023,3,10,10,44,59,2231)), datetime(2023, 3,10,10,30,0,0) )
        self.assertEqual( tf_15m(datetime(2023,3,10,10,15, 0,   1)), datetime(2023, 3,10,10,15,0,0) )
        self.assertEqual( tf_15m(datetime(2023,3,10,10, 0, 0,   0)), datetime(2023, 3,10,10, 0,0,0) )
        tf_30m = DataInterval.MIN30.floor
        self.assertEqual( tf_30m(datetime(2023,3,10,10,58,22, 444)), datetime(2023, 3,10,10,30,0,0) )
        self.assertEqual( tf_30m(datetime(2023,3,10,10,20,55,1234)), datetime(2023, 3,10,10, 0,0,0) )
        tf_1h = DataInterval.HOUR1.floor
        self.assertEqual(  tf_1h(datetime(2023,3,10,10,58,22, 444)), datetime(2023, 3,10,10, 0,0,0) )
        self.assertEqual(  tf_1h(datetime(2023,3,10,10,20,55,1234)), datetime(2023, 3,10,10, 0,0,0) )
        tf_1d = DataInterval.DAY1.floor
        self.assertEqual(  tf_1d(datetime(2023,3,10,11, 1,46,6219)), datetime(2023, 3,10, 0, 0,0,0) )
        tf_1w = DataInterval.WEEK1.floor
        self.assertEqual(  tf_1w(datetime(2023,3,10,11, 1,55,6219)), datetime(2023, 3, 6, 0, 0,0,0) )
        self.assertEqual(  tf_1w(datetime(2023,1, 1, 1, 1, 1,   1)), datetime(2022,12,26, 0, 0,0,0) )
        tf_1mo = DataInterval.MONTH1.floor
        self.assertEqual( tf_1mo(datetime(2023,3,10,11, 1,55,6219)), datetime(2023, 3, 1, 0, 0,0,0) )
        self.assertEqual( tf_1mo(datetime(2023,1, 1, 1, 1, 1,   1)), datetime(2023, 1, 1, 0, 0,0,0) )
        # check at the edges
        self.assertEqual( tf_30m(datetime(2023,3,10,10,29,59,999999)), datetime(2023, 3,10,10, 0,0,0) )
        self.assertEqual( tf_30m(datetime(2023,3,10,10,30, 0,     0)), datetime(2023, 3,10,10,30,0,0) )
        self.assertEqual( tf_30m(datetime(2023,3,10,10,30, 0,     1)), datetime(2023, 3,10,10,30,0,0) )
        self.assertEqual( tf_30m(datetime(2023,3,10,10,30, 1,     0)), datetime(2023, 3,10,10,30,0,0) )
        self.assertEqual( tf_15m(datetime(2023,3,10,10,29,59,999999)), datetime(2023, 3,10,10,15,0,0) )
        self.assertEqual( tf_15m(datetime(2023,3,10,10,30, 0,     0)), datetime(2023, 3,10,10,30,0,0) )
        self.assertEqual( tf_15m(datetime(2023,3,10,10,30, 0,     1)), datetime(2023, 3,10,10,30,0,0) )
        self.assertEqual( tf_15m(datetime(2023,3,10,10,30, 1,     0)), datetime(2023, 3,10,10,30,0,0) )

    def test_metadata_logger(self):
        self.maxDiff = None
        md = load_logger_metadata( Path(__file__).parent/'TestLogger.json' )
        #from pprint import pprint
        #with open("expect.txt","w",encoding="UTF-8") as fh: pprint(_TestLogger_md, stream=fh)
        #with open("got.txt","w",encoding="UTF-8") as fh: pprint(md, stream=fh)
        self.assertEqual( md, _TestLogger_md )
        self.assertEqual( md.tables['Hourly'].mappings['Press_Humid'].old_idxs, (0,8,7) )
        self.assertEqual( "TestLogger/Daily", md.tables['Daily'].tblident )
        self.assertEqual( "TestLogger/Hourly", md.tables['Hourly'].tblident )
        for tbl in ("Daily","Hourly"):
            for ci, col in enumerate(md.tables[tbl].columns):
                for k,v in _TestLogger_props[tbl][ci].items():
                    if k == 'csv': continue  # the .csv property was moved into .hdr
                    self.assertEqual( getattr(col, k), v )
                self.assertEqual( col.hdr.csv, _TestLogger_props[tbl][ci]['csv'] )
                self.assertEqual( col.tup, (col.name, col.unit, col.prc) )
        self.assertEqual( md.tables['Daily'].sql, "testlogger_daily" )
        self.assertEqual( md.tables['Hourly'].sql, "testlogger_hourly" )
        self.assertEqual( md.tables['Hourly'].mappings['Press_Humid'].sql, "press_humid" )

    def test_metadata_times(self):
        md1 = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"+05:30","min_datetime":"2023-01-01 12:34:56","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        self.assertEqual( md1.tz, timezone(timedelta(seconds=(5*60+30)*60)) )
        self.assertEqual( md1.min_datetime.isoformat(), "2023-01-01T12:34:56+05:30" )
        md2 = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"+05:30","min_datetime":"2023-01-01 12:34:56+06:00","tables":{"foo":{"prikey":0,"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        self.assertEqual( md2.min_datetime.isoformat(), "2023-01-01T12:34:56+06:00" )

    def test_metadata_intervals(self):
        self.assertEqual( load_logger_metadata(
            b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}'
            ).tables['foo'].interval, DataInterval.UNDEF )
        self.assertEqual( load_logger_metadata(
            b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"interval":"15min","columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}'
            ).tables['foo'].interval, DataInterval.MIN15 )
        self.assertEqual( load_logger_metadata(
            b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"interval":"30min","columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}'
            ).tables['foo'].interval, DataInterval.MIN30 )
        self.assertEqual( load_logger_metadata(
            b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"interval":"1hour","columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}'
            ).tables['foo'].interval, DataInterval.HOUR1 )
        self.assertEqual( load_logger_metadata(
            b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"interval":"1day","columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}'
            ).tables['foo'].interval, DataInterval.DAY1 )
        self.assertEqual( load_logger_metadata(
            b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"interval":"1week","columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}'
            ).tables['foo'].interval, DataInterval.WEEK1 )
        self.assertEqual( load_logger_metadata(
            b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"interval":"1month","columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}'
            ).tables['foo'].interval, DataInterval.MONTH1 )
        with self.assertRaises(RuntimeError):  # "failed to validate" instead of the ValueError thrown from load_logger_metadata
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"interval":"foo","columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')

    def test_metadata_errors(self):
        with self.assertRaises(RuntimeError): load_logger_metadata(b'{}')
        bmd = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        with tempcopy(bmd) as md:
            md.logger_name = "Foo$"
            with self.assertRaises(ValueError): md.validate()
        with self.assertRaises(ValueError): MdBaseCol(name="xy$",unit="",prc="").validate()
        with self.assertRaises(ValueError): MdBaseCol(name="xy",unit="xy[",prc="").validate()
        with self.assertRaises(ValueError): MdBaseCol(name="xy",unit="",prc="xy$").validate()
        with tempcopy(bmd) as md:
            md.tables['foo'].parent = None
            with self.assertRaises(TypeError): md.tables['foo'].validate()
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            t = md.tables['foo']
            md.tables.clear()
            with self.assertRaises(ValueError): t.validate()
        with tempcopy(bmd) as md:
            md.tables['foo'].prikey = 1
            with self.assertRaises(IndexError): md.validate()
        with tempcopy(bmd) as md:
            md.toa5_env_match.station_name = None
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.toa5_env_match = None
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.logger_type = 0
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.variants = []
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.sensors = []
            with self.assertRaises(ValueError): md.validate()
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","sensors":{"xyz":" "},"toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS","sens":"xyz"}]}}}')
        with tempcopy(bmd) as md:
            md.tables['foo'].name = "Foo"
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.tables['foo'].columns[0].var = "foo"
            with self.assertRaises(RuntimeError): md.validate()
        with self.assertWarns(UserWarning) as wcm:
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS","type":"TimestampNoTz"},{"name":"xy","type":"TimestampWithTz"}]}}}')
        self.assertIn("mixed TimestampNoTz/WithTz types", str(wcm.warning))
        with self.assertWarns(UserWarning) as wcm:
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS","type":"TimestampWithTz"}]}}}')
        self.assertIn("doesn't have a TZ set", str(wcm.warning))
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS","type":"TimestampNoTz"}]}}}')
        with tempcopy(bmd) as md:
            md.tables['foo'].mappings['xy'] = MdMapping( name="xyz", type=MappingType.VIEW, map=[] )
            with self.assertRaises(RuntimeError): md.validate()
        with tempcopy(bmd) as md:
            md.tables['foo'].mappings['xyz'] = MdMapping( name="xyz", type=MappingType.VIEW, map=[
                MdMapEntry( old=MdBaseCol(name="foo"), new=MdBaseCol(name="bar") ) ] )
            with self.assertRaises(RuntimeError): md.validate()
        with tempcopy(bmd) as md:
            md.tables['foo'].mappings['xyz'] = MdMapping( name="xyz", type=MappingType.VIEW, map=[
                MdMapEntry( old=MdBaseCol(name="TIMESTAMP",unit="TS"), new=MdBaseCol(name="TIMESTAMP",unit="TS") ) ] )
            with self.assertRaises(RuntimeError): md.validate()
        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            MdMapping( name="xyz", type=None, map=[] ).validate()
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS","sens":"xy"}]}}}')
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"foo"}]}}}')
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","sensors":{"xyz":"abc"},"toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","variants":["abc","def"],"toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        with tempcopy(bmd) as md:
            md.tz = 'Foo'
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.tz = timezone(timedelta(seconds=3*60*60))
            md.tables['foo'].columns[0].type = TimestampNoTz()
            with self.assertWarns(UserWarning) as wcm: md.validate()
            self.assertEqual("Table foo has TimestampNoTz columns and non-UTC timezone (converstion to UTC recommended!)", str(wcm.warning))
        with tempcopy(bmd) as md:
            md.tables['foo'].columns[0].lodt = 'Foo'
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.tz = None
            md.known_gaps = (TimeRange(why="x",start=datetime.fromisoformat("2023-01-02 03:04:05")),)
            with self.assertRaises(ValueError): md.validate()
        with tempcopy(bmd) as md:
            md.tz = None
            md.known_gaps = (TimeRange(why="x",start=datetime.fromisoformat("2023-01-02 03:04:05Z"),end=datetime.fromisoformat("2023-01-02 03:04:06")),)
            with self.assertRaises(ValueError): md.validate()
        with self.assertRaises(RuntimeError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","ignore_tables":[],"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        with self.assertRaises(RuntimeError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","ignore_tables":["hello","hello"],"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","ignore_tables":["foo"],"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            MdKnownIssue( type=KnownIssueType.BAD, cols=(), when=TimeRange(why="x",start=datetime.fromisoformat("2023-01-02 03:04:05")) ).validate()
        with self.assertRaises(ValueError):
            # noinspection PyTypeChecker
            MdKnownIssue( type=None, cols=("foo",), when=TimeRange(why="x",start=datetime.fromisoformat("2023-01-02 03:04:05")) ).validate()
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}],'
                                 b'"known_issues":[{"type":"unusual","cols":["bar"],"when":{"time":"2023-08-07 15:00:00Z","why":"x"}}]}}}')

    def test_metadata_collection(self):
        md1 = load_logger_metadata( Path(__file__).parent/'TestLogger.json' )
        md1t1 = md1.tables['Daily']
        md1t2 = md1.tables['Hourly']
        md2 = _DummyLogger_md
        md2t1 = md2.tables['Daily']
        # noinspection PyPep8Naming
        MdC = MdCollection

        coll1 = MdC(md1,md2)
        self.assertEqual( tuple(coll1), (md1, md2) )
        self.assertEqual( tuple(coll1.tables), (md1t1, md1t2, md2t1) )
        self.assertIn( md1, coll1 )
        self.assertIn( md2, coll1 )
        self.assertIn( md1t1, coll1 )
        self.assertIn( md1t2, coll1 )
        self.assertIn( md2t1, coll1 )
        self.assertEqual( coll1[0], md1 )
        self.assertEqual( tuple(reversed(coll1)), (md2, md1) )

        coll2 = MdC(md1t1,md1t1)
        self.assertEqual( tuple(coll2), (md1,) )
        self.assertEqual( tuple(coll2.tables), (md1t1,) )
        self.assertIn( md1, coll2 )
        self.assertNotIn( md2, coll2 )
        self.assertIn( md1t1, coll2 )
        self.assertNotIn( md1t2, coll2 )
        self.assertNotIn( md2t1, coll2 )

        with self.assertRaises(ValueError): MdC()  # no metadatas or tables
        with self.assertRaises(ValueError): MdC("foo")  # table can't be found
        with self.assertRaises(ValueError): MdC(md1, md2t1)  # table not in metadatas
        with self.assertRaises(ValueError): MdC(md1, md2, "Daily")  # table name appears in >1 metadatas
        with self.assertRaises(ValueError): MdC(md1, md2, "foo")  # table name not found

        coll3 = MdC(md1,'Hourly',md2,md1,'Hourly',md1t2,md2,md2)
        self.assertEqual( tuple(coll3), (md1,md2) )
        self.assertEqual( tuple(coll3.tables), (md1t2,) )
        self.assertIn( md1, coll3 )
        self.assertIn( md2, coll3 )
        self.assertNotIn( md1t1, coll3 )
        self.assertIn( md1t2, coll3 )
        self.assertNotIn( md2t1, coll3 )

        self.assertEqual( MdC(md1), MdC(md1) )
        self.assertEqual( MdC(MdC(md2t1)), MdC(md2t1) )
        self.assertNotEqual( MdC(md1), (md1,) )

        with tempcopy(md2) as md3:
            md3.tables.clear()
            with self.assertRaises(ValueError): MdC(md3)  # no tables

        with tempcopy(md2) as md4:
            md4.logger_name = md1.logger_name
            with self.assertRaises(ValueError): MdC(md1,md4)  # duplicate logger name

    def test_timerange_parse(self):
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"known_gaps":[{"time":"2023-08-07 13:00:00","end":"2023-08-07 14:00:00Z","why":"x"}],"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        with self.assertRaises(ValueError):
            load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"known_gaps":[{"time":"2023-08-07 13:00:00Z","end":"2023-08-07 14:00:00","why":"x"}],"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        md1 = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","known_gaps":[{"time":"open","end":"2023-08-07 14:00:00","why":"x"}],"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        self.assertEqual( md1.known_gaps[0].start, datetime.min.replace(tzinfo=timezone.utc) )
        self.assertEqual( md1.known_gaps[0].end, datetime(2023,8,7,14,tzinfo=timezone.utc) )
        md2 = load_logger_metadata(b'{"logger_name":"Foo","toa5_env_match":{"station_name":"Foo"},"tz":"UTC","known_gaps":[{"time":"2023-08-07 13:00:00","end":"open","why":"x"}],"tables":{"foo":{"columns":[{"name":"TIMESTAMP","unit":"TS"}]}}}')
        self.assertEqual( md2.known_gaps[0].start, datetime(2023,8,7,13,tzinfo=timezone.utc) )
        self.assertEqual( md2.known_gaps[0].end, datetime.max.replace(tzinfo=timezone.utc) )

    def test_timerange(self):
        TimeRange(why="x", start=datetime.fromisoformat("2023-01-02 03:04:05Z"), end=datetime.fromisoformat("2023-01-02 03:04:06Z")).validate()
        with self.assertRaises(ValueError):
            TimeRange(why=" \t\n ", start=datetime.fromisoformat("2023-01-02 03:04:05Z")).validate()
        with self.assertRaises(ValueError):
            TimeRange(why="x", start=datetime.fromisoformat("2023-01-02 03:04:05Z"), end=datetime.fromisoformat("2023-01-02 03:04:05Z")).validate()
        with self.assertRaises(ValueError):
            TimeRange(why="x", start=datetime.fromisoformat("2023-01-02 03:04:05Z"), end=datetime.fromisoformat("2023-01-02 03:04:04Z")).validate()
        with self.assertRaises(ValueError):
            TimeRange(why="x", start=datetime.fromisoformat("2023-01-02 03:04:05"), end=datetime.fromisoformat("2023-01-02 03:04:06Z")).validate()
        with self.assertRaises(ValueError):
            TimeRange(why="x", start=datetime.fromisoformat("2023-01-02 03:04:05Z"), end=datetime.fromisoformat("2023-01-02 03:04:06")).validate()
        def mkrngset(*inp):
            for x,y in inp:
                yield TimeRange(why=x, start=datetime.fromisoformat(x), end=datetime.fromisoformat(y) if y else None)
        TimeRange.validate_set( tuple(mkrngset(
            ("2023-01-02 03:04:00Z", "2023-01-02 03:04:30Z"),
            ("2023-01-02 03:05:00Z", "2023-01-02 03:05:30Z"),
            ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
            ("2023-01-02 03:07:00Z", None),
            ("2023-01-02 03:08:00Z", None),
        )) )
        with self.assertRaises(ValueError):
            TimeRange.validate_set( tuple(mkrngset(
                ("2023-01-02 03:04:00Z", "2023-01-02 03:04:30Z"),
                ("2023-01-02 03:04:10Z", "2023-01-02 03:04:20Z"),  # inside the first set
                ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
                ("2023-01-02 03:07:00Z", None),
                ("2023-01-02 03:08:00Z", None),
            )) )
        with self.assertRaises(ValueError):
            TimeRange.validate_set( tuple(mkrngset(
                ("2023-01-02 03:05:10Z", "2023-01-02 03:05:20Z"),  # inside the second set
                ("2023-01-02 03:05:00Z", "2023-01-02 03:05:30Z"),
                ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
                ("2023-01-02 03:07:00Z", None),
                ("2023-01-02 03:08:00Z", None),
            )) )
        with self.assertRaises(ValueError):
            TimeRange.validate_set( tuple(mkrngset(
                ("2023-01-02 03:04:00Z", "2023-01-02 03:05:10Z"),  # overlaps with second set
                ("2023-01-02 03:05:00Z", "2023-01-02 03:05:30Z"),
                ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
                ("2023-01-02 03:07:00Z", None),
                ("2023-01-02 03:08:00Z", None),
            )) )
        with self.assertRaises(ValueError):
            TimeRange.validate_set( tuple(mkrngset(
                ("2023-01-02 03:04:00Z", "2023-01-02 03:04:30Z"),
                ("2023-01-02 03:04:20Z", "2023-01-02 03:05:30Z"),  # overlaps with first set
                ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
                ("2023-01-02 03:07:00Z", None),
                ("2023-01-02 03:08:00Z", None),
            )) )
        with self.assertRaises(ValueError):
            TimeRange.validate_set( tuple(mkrngset(
                ("2023-01-02 03:04:00Z", "2023-01-02 03:04:30Z"),
                ("2023-01-02 03:04:15Z", None),  # inside the first set
                ("2023-01-02 03:05:00Z", "2023-01-02 03:05:30Z"),
                ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
                ("2023-01-02 03:07:00Z", None),
            )) )
        with self.assertRaises(ValueError):
            TimeRange.validate_set( tuple(mkrngset(
                ("2023-01-02 03:04:15Z", None),  # inside the first set
                ("2023-01-02 03:04:00Z", "2023-01-02 03:04:30Z"),
                ("2023-01-02 03:05:00Z", "2023-01-02 03:05:30Z"),
                ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
                ("2023-01-02 03:07:00Z", None),
            )) )
        with self.assertRaises(ValueError):
            TimeRange.validate_set( tuple(mkrngset(
                ("2023-01-02 03:04:00Z", "2023-01-02 03:04:30Z"),
                ("2023-01-02 03:05:00Z", "2023-01-02 03:05:30Z"),
                ("2023-01-02 03:06:00Z", "2023-01-02 03:06:30Z"),
                ("2023-01-02 03:07:00Z", None),
                ("2023-01-02 03:07:00Z", None),  # same as previous timestamp
            )) )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
