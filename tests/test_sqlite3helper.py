#!/usr/bin/env python
"""Tests for Sqlite3 Helper.

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
from tempfile import TemporaryDirectory
from sqlite3helper import load_driver, quote, Table, Column, \
    InsertHelper, RowMismatchError, CanExecute, DriverModule, VaccuumHelper
from textwrap import dedent
from contextlib import closing

testcases :dict[Table, dict[str, str | tuple[str, ...] | tuple[tuple[str, ...], ...] ]] = {
    Table("foo1", (Column("hello","TEXT PRIMARY KEY"), Column("world","INTEGER","foobar")) ): {
        "create_sql": (
            dedent("""\
            CREATE TABLE "foo1" (
            \t"hello" TEXT PRIMARY KEY,
            \t"world" INTEGER  -- foobar
            );"""),
            dedent("""\
            CREATE TRIGGER "foo1_modify" BEFORE UPDATE ON "foo1" FOR EACH ROW
            \tWHEN ( OLD."world" IS NOT NEW."world" )
            \tBEGIN SELECT RAISE(ABORT, "same primary key but different values"); END;"""),
            """CREATE TRIGGER "foo1_nodelete" BEFORE DELETE ON "foo1" BEGIN SELECT RAISE(ABORT, "deletion not allowed"); END;""",
        ),
        "insert_sql": dedent("""\
            INSERT INTO "foo1" ("hello","world")
            \tVALUES (?,?)
            \tON CONFLICT ("hello") DO UPDATE SET "world"=EXCLUDED."world";"""),
        "select_sql": """SELECT "hello", "world" FROM "foo1\"""",
        "where_pk_sql": """WHERE "hello"=?""",
        "order_pk_sql": """ORDER BY "hello" ASC""",
        "_ins_rows": ( ("foo",2), ("quz",3), ("foo",2), ("Foo",2), ),
        "_err_rows": ( ("foo",3), ),
        "_sel_rows": ( ("Foo",2), ("foo",2), ("quz",3), ),
    },
    Table("foo2", (Column("hello","INTEGER PRIMARY KEY"), Column("world")), prikey_is_datetime=True): {
        "create_sql": (
            dedent("""\
            CREATE TABLE "foo2" (
            \t"hello" INTEGER PRIMARY KEY,  -- datetime
            \t"world" TEXT
            );"""),
            dedent("""\
            CREATE TRIGGER "foo2_modify" BEFORE UPDATE ON "foo2" FOR EACH ROW
            \tWHEN ( OLD."world" IS NOT NEW."world" )
            \tBEGIN SELECT RAISE(ABORT, "same primary key but different values"); END;"""),
            """CREATE TRIGGER "foo2_nodelete" BEFORE DELETE ON "foo2" BEGIN SELECT RAISE(ABORT, "deletion not allowed"); END;""",
        ),
        "insert_sql": dedent("""\
            INSERT INTO "foo2" ("hello","world")
            \tVALUES (CAST(STRFTIME('%s',?) AS INTEGER),?)
            \tON CONFLICT ("hello") DO UPDATE SET "world"=EXCLUDED."world";"""),
        "select_sql": """SELECT STRFTIME("%Y-%m-%d %H:%M:%SZ","hello",'unixepoch') AS "hello", "world" FROM "foo2\"""",
        "where_pk_sql": """WHERE "hello"=CAST(STRFTIME('%s',?) AS INTEGER)""",
        "order_pk_sql": """ORDER BY "hello" ASC""",
        "_ins_rows": (
            ("2023-06-26 19:00Z","FooBar"),
            ("2023-06-26 19:00:00Z","FooBar"),
            ("2023-06-26 19:00+00:00","FooBar"),
            ("2023-06-26T19:00:00Z","FooBar"),
            ("2023-06-26 19:00:01Z","FooBar"),
        ),
        "_err_rows": (
            ("2023-06-26 19:00:00Z", "Foobar"),
        ),
        "_sel_rows": (
            ("2023-06-26 19:00:00Z","FooBar"),
            ("2023-06-26 19:00:01Z","FooBar"),
        ),
    },
    Table("foo3", (Column("foo","TEXT","Foo"), Column("bar","TEXT PRIMARY KEY"), Column("baz")) ): {
        "create_sql": (
            dedent("""\
            CREATE TABLE "foo3" (
            \t"foo" TEXT,  -- Foo
            \t"bar" TEXT PRIMARY KEY,
            \t"baz" TEXT
            );"""),
            dedent("""\
            CREATE TRIGGER "foo3_modify" BEFORE UPDATE ON "foo3" FOR EACH ROW
            \tWHEN ( OLD."foo" IS NOT NEW."foo" OR OLD."baz" IS NOT NEW."baz" )
            \tBEGIN SELECT RAISE(ABORT, "same primary key but different values"); END;"""),
            """CREATE TRIGGER "foo3_nodelete" BEFORE DELETE ON "foo3" BEGIN SELECT RAISE(ABORT, "deletion not allowed"); END;""",
        ),
        "insert_sql": dedent("""\
            INSERT INTO "foo3" ("foo","bar","baz")
            \tVALUES (?,?,?)
            \tON CONFLICT ("bar") DO UPDATE SET "foo"=EXCLUDED."foo", "baz"=EXCLUDED."baz";"""),
        "select_sql": """SELECT "foo", "bar", "baz" FROM "foo3\"""",
        "where_pk_sql": """WHERE "bar"=?""",
        "order_pk_sql": """ORDER BY "bar" ASC""",
        "_ins_rows": ( ("a","b","c"), ("a","b","c"), ("a","b","c") ),
        "_err_rows": ( ("A","b","c"), ("a","b","C") ),
        "_sel_rows": ( ("a","b","c"), ),
    },
    Table("foo4", (Column("foo","TEXT","blah!"), Column("bar","INTEGER PRIMARY KEY","Bar"), Column("quz")), prikey_is_datetime=True): {
        "create_sql": (
            dedent("""\
            CREATE TABLE "foo4" (
            \t"foo" TEXT,  -- blah!
            \t"bar" INTEGER PRIMARY KEY,  -- datetime; Bar
            \t"quz" TEXT
            );"""),
            dedent("""\
            CREATE TRIGGER "foo4_modify" BEFORE UPDATE ON "foo4" FOR EACH ROW
            \tWHEN ( OLD."foo" IS NOT NEW."foo" OR OLD."quz" IS NOT NEW."quz" )
            \tBEGIN SELECT RAISE(ABORT, "same primary key but different values"); END;"""),
            """CREATE TRIGGER "foo4_nodelete" BEFORE DELETE ON "foo4" BEGIN SELECT RAISE(ABORT, "deletion not allowed"); END;""",
        ),
        "insert_sql": dedent("""\
            INSERT INTO "foo4" ("foo","bar","quz")
            \tVALUES (?,CAST(STRFTIME('%s',?) AS INTEGER),?)
            \tON CONFLICT ("bar") DO UPDATE SET "foo"=EXCLUDED."foo", "quz"=EXCLUDED."quz";"""),
        "select_sql": """SELECT "foo", STRFTIME("%Y-%m-%d %H:%M:%SZ","bar",'unixepoch') AS "bar", "quz" FROM "foo4\"""",
        "where_pk_sql": """WHERE "bar"=CAST(STRFTIME('%s',?) AS INTEGER)""",
        "order_pk_sql": """ORDER BY "bar" ASC""",
        "_ins_rows": (
            ("hello","2023-06-27T12:34:56+00:00","world"),
            ("hi","2023-06-27T12:34:56+01:00","there"),
            ("hello","2023-06-27 12:34:56Z","world"),
        ),
        "_err_rows": (
            ("hello","2023-06-27T11:34:56-01:00","World"),
        ),
        "_sel_rows": (
            ("hi","2023-06-27 11:34:56Z","there"),
            ("hello","2023-06-27 12:34:56Z","world"),
        ),
    },
}

class MockConn(CanExecute):
    def __init__(self, driver :DriverModule):
        self.driver = driver
    def execute(self, *args, **kwargs):
        raise self.driver.dbapi2.IntegrityError("something happened")
    def close(self): pass  # pragma: no cover

class TestSqlite3Helper(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.drv = load_driver(verbose=False)

    def test_quote(self):
        self.assertEqual( quote('hello'), '"hello"' )
        self.assertEqual( quote('H€llö, "Wörld'), '"H€llö, ""Wörld"' )
        with self.assertRaises(ValueError): quote("X\x00Y")

    def test_tables(self):
        with closing( self.drv.connect(':memory:') ) as con:
            for tbl, props in testcases.items():
                tbl.validate()
                self.assertTrue( all( x in props for x in ("create_sql","insert_sql","select_sql","where_pk_sql","order_pk_sql") ) )
                for k, v in props.items():
                    if k.startswith("_"): continue
                    self.assertEqual( getattr(tbl,k), v )
                for s in tbl.create_sql:
                    con.execute(s)
                ins = InsertHelper(tbl, self.drv, con)
                for row in props["_ins_rows"]:
                    ins.insert(row)
                for row in props["_err_rows"]:
                    with self.assertRaises(RowMismatchError):
                        ins.insert(row)
                self.assertEqual( props["_sel_rows"], tuple(con.execute(tbl.select_sql + " "+ tbl.order_pk_sql).fetchall()) )

    def test_inserthelper(self):
        # note the main code is already tested above; this just tests some additional error cases
        tbl = Table("foo", (Column("Timestamp","INTEGER PRIMARY KEY"),), prikey_is_datetime=True )
        con = MockConn(self.drv)
        ins = InsertHelper(tbl, self.drv, con)
        with self.assertRaises(self.drv.dbapi2.IntegrityError):
            ins.insert(("2023-04-05T12:34:56Z",))
        with self.assertRaises(ValueError):
            ins.insert(("2023-04-05T12:34:56",))

    def test_rowdiff(self):
        tbl = Table("foo", (Column("Timestamp","INTEGER PRIMARY KEY"),
            Column("one"), Column("two"), Column("three"), Column("four")), prikey_is_datetime=True )
        with closing( self.drv.connect(':memory:') ) as con:
            for s in tbl.create_sql: con.execute(s)
            ins = InsertHelper(tbl, self.drv, con)
            ins.insert( ("2023-04-05T12:34:56Z", "1", "2", "3", "4") )
            with self.assertRaises(RowMismatchError) as cm:
                ins.insert( ("2023-04-05T12:34:56Z", "1", "2", "3", "5") )
            self.assertEqual( cm.exception.rowdiff, dedent("""\
                --- existing_row
                +++ insert_row
                @@ -1 +1 @@
                -('2023-04-05 12:34:56Z', '1', '2', '3', '4')
                +('2023-04-05T12:34:56Z', '1', '2', '3', '5')""") )
            ins.insert( ("2023-05-06 12:34:56Z",
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "Curabitur sollicitudin urna maximus imperdiet feugiat.",
                "Aliquam feugiat lacus eu elementum placerat.",
                "Sed tincidunt enim commodo maximus accumsan." ) )
            with self.assertRaises(RowMismatchError) as cm:
                ins.insert( ("2023-05-06 12:34:56Z",
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                    "Curabitur sollicitudin urna maximus imperdiet feugiat.",
                    "Aliquam feugiat purus eu elementum placerat.",
                    "Sed tincidunt enim commodo maximus accumsan." ) )
            self.assertEqual( cm.exception.rowdiff, dedent("""\
                --- existing_row
                +++ insert_row
                @@ -1,5 +1,5 @@
                 ('2023-05-06 12:34:56Z',
                  'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
                  'Curabitur sollicitudin urna maximus imperdiet feugiat.',
                - 'Aliquam feugiat lacus eu elementum placerat.',
                + 'Aliquam feugiat purus eu elementum placerat.',
                  'Sed tincidunt enim commodo maximus accumsan.')""") )

    def test_vacuumhelper(self):
        with TemporaryDirectory() as td:
            with VaccuumHelper(':memory:', sqlite3mod=self.drv): pass
            with VaccuumHelper(td+'/test1', sqlite3mod=self.drv, memvacuum=True): pass
            with VaccuumHelper(td+'/test2', sqlite3mod=self.drv, memvacuum=True, sync=False): pass
            with VaccuumHelper(td+'/test1', sqlite3mod=self.drv, vacuum=True): pass
            with VaccuumHelper(td+'/test1', sqlite3mod=self.drv, vacuum=True, sync=False): pass
            with self.assertRaises(FileExistsError):
                with VaccuumHelper(td+'/test1', sqlite3mod=self.drv, memvacuum=True): pass
        with self.assertRaises(ValueError):  # can't use vacuum+memvacuum
            with VaccuumHelper(td+"/test", sqlite3mod=self.drv, vacuum=True, memvacuum=True): pass
        with self.assertRaises(ValueError):  # memvacuum into memory doesn't make sense
            with VaccuumHelper(':memory:', sqlite3mod=self.drv, memvacuum=True): pass

    def test_table_errs(self):
        with self.assertRaises(ValueError):  # no cols
            Table("foo", ()).validate()
        with self.assertRaises(ValueError):  # no pk
            Table("foo", (Column("bar"),)).validate()
        with self.assertRaises(ValueError):  # more than one pk
            Table("foo", (Column("bar","PRIMARY KEY"), Column("quz","PRIMARY KEY"))).validate()
        with self.assertRaises(ValueError):  # pk wrong type
            Table("foo", (Column("bar","TEXT PRIMARY KEY"),), prikey_is_datetime=True).validate()
        with self.assertRaises(ValueError):  # bad comment
            Table("foo", (Column("bar","PRIMARY KEY","hello\nworld"),) ).validate()

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
