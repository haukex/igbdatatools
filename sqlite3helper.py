#!python3
"""Helpers for SQLite3 databases used as logger data storage.

The functions in this module provide helpers for our use case of importing
raw logger data into SQLite3 databases. Data loggers usually have circular
buffers for logging data, and since these are usually not cleared after
readouts, each readout into a file will usually contain (many) duplicated
records across multiple files. On importing these records, we'd like to
both ignore exact duplicates, but also get errors if for some reason there
are two records with the same primary key (usually timestamps) but different
data. This class provides SQLite3 table definitions with a ``TRIGGER``
and a corresponding ``INSERT`` statement that provides this functionality.

Note that if the primary key is a datetime value, the functions in this
module will generally use the format ``YYYY-MM-DD HH:MM:SSZ`` (with a few
minor variations on this format allowed on input), e.g. the ``INSERT``
generated by this module will expect the input as a string in this format,
and the generated ``SELECT`` will return values in this format. However,
in the SQLite3 database, the column will be an ``INTEGER PRIMARY KEY``
column (i.e. an alias for SQLite's "rowid") holding the Unix timestamp.

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
import sys
import os
import re
from functools import cache
from contextlib import contextmanager, closing
from types import ModuleType
from typing import NamedTuple, Optional, Protocol, runtime_checkable, Self
from collections.abc import Sequence, Iterable
from igbpyutils.file import Filename

# try to make the type checker a little happier with the following defs...
@runtime_checkable
class DummyCursor(Iterable, Protocol):  # pragma: no cover
    def fetchone(self) -> Sequence: ...
    def fetchall(self) -> list[Sequence]: ...
    def close(self): ...
@runtime_checkable
class CanExecute(Protocol):  # pragma: no cover
    def execute(self, *args, **kwargs) -> DummyCursor: ...
    def close(self): ...
@runtime_checkable
class CanConnect(Protocol):  # pragma: no cover
    def connect(self, *args, **kwargs) -> CanExecute: ...
DriverModule = ModuleType | CanConnect

def load_driver(*, verbose :bool = True) -> DriverModule:
    """Loads either :module:`sqlite3`, or, if its version is too low, loads :module:`pysqlite3` instead.

    We need at least 3.35.0 for Generalized ``UPSERT`` and ``RETURNING``;
    see https://www.sqlite.org/changes.html#version_3_35_0

    The latter can be installed via ``pip install pysqlite3-binary``;
    for more information see https://github.com/coleifer/pysqlite3"""
    import sqlite3
    if sqlite3.sqlite_version_info < (3,35,0):
        # noinspection PyPackageRequirements
        import pysqlite3
        if pysqlite3.sqlite_version_info < (3,35,0):  # pragma: no cover
            raise ImportError(f"Need a recent SQLite version ({sqlite3.sqlite_version=}, {pysqlite3.sqlite_version=})")
        if verbose:  # pragma: no cover
            print(f"Loaded pysqlite3 ({sqlite3.sqlite_version=}, {pysqlite3.sqlite_version=})", file=sys.stderr)
        return pysqlite3
    else:  # pragma: no cover
        if verbose:
            print(f"Loaded sqlite3 ({sqlite3.sqlite_version=})", file=sys.stderr)
        return sqlite3

# A subset of https://www.sqlite.org/lang_datefunc.html#time_values
_sqlite_datetime_re = re.compile(r'''\A\d{4}-\d\d-\d\d[ T]\d\d:\d\d(?::\d\d)?(?:Z|[+-]\d\d:\d\d)\Z''')

_prikey_re = re.compile(r'''\bPRIMARY\s+KEY\b''',re.IGNORECASE)
_intprikey_re = re.compile(r'''\A\s*INTEGER\s+PRIMARY\s+KEY\s*\Z''', re.IGNORECASE)

_mismatch_message= "same primary key but different values"

def quote(s :str) -> str:
    """Quote a string for use in ``sqlite3``, e.g. as an identifier.

    Used internally in this module, so you'll only need this if you're building your own SQL strings.
    Based on https://stackoverflow.com/a/6701665"""
    s.encode("UTF-8", errors="strict").decode("UTF-8", errors="strict")
    if "\x00" in s: raise ValueError("NUL characters not allowed in identifiers")
    return '"' + s.replace('"', '""') + '"'

class Column(NamedTuple):
    """Represents a column in a :class:`Table`."""
    name :str
    type :str = "TEXT"
    comment :Optional[str] = None

class Table(NamedTuple):
    """Represents an SQLite3 table."""
    name :str
    columns :tuple[Column, ...]
    prikey_is_datetime :bool = False

    @property
    @cache
    def prikey_col_idx(self) -> int:
        """The index of the primary key in the :property:`columns`, detected via the :property:`Column.type`."""
        if prikeys := tuple( i for i,c in enumerate(self.columns) if _prikey_re.search(c.type) ):
            if len(prikeys)>1: raise ValueError(f"more than one primary key column found in table {self.name!r}")
            return prikeys[0]
        raise ValueError(f"no primary key column found in table {self.name!r}")

    def validate(self) -> Self:
        """Perform some checks on this table definition."""
        if not self.columns:
            raise ValueError(f"table {self.name!r} has no columns")
        for col in self.columns:
            if col.comment and ("\n" in col.comment or "\r" in col.comment):
                raise ValueError(f"invalid comment {col.comment!r}")
        pki = self.prikey_col_idx  # does some validation as well
        if self.prikey_is_datetime and not _intprikey_re.fullmatch(self.columns[pki].type):
            raise ValueError(f"prikey_is_datetime requires an INTEGER PRIMARY KEY column, but table {self.name!r}'s primary key column is {self.columns[pki].type!r}")
        return self

    @property
    @cache
    def create_sql(self) -> tuple[str, ...]:
        """The SQL statements needed to create the table in the database."""
        self.validate()
        pki = self.prikey_col_idx
        modifytrig_cond = []
        coldefs :list[str] = []
        for i, col in enumerate(self.columns):
            coldef = f"\t{quote(col.name)} {col.type}"
            if i<len(self.columns)-1: coldef+=","
            if self.prikey_is_datetime and i==pki:
                coldef += f"  -- datetime"
                if col.comment: coldef += f"; {col.comment}"
            elif col.comment:
                coldef += f"  -- {col.comment}"
            coldefs.append(coldef)
            if i!=pki: modifytrig_cond.append(f"OLD.{quote(col.name)} IS NOT NEW.{quote(col.name)}")
        return (
            f"CREATE TABLE {quote(self.name)} (\n" + "\n".join(coldefs) + "\n);",
            f"CREATE TRIGGER {quote(self.name + '_modify')} BEFORE UPDATE ON {quote(self.name)} FOR EACH ROW\n\tWHEN ( "
            + " OR ".join(modifytrig_cond) + " )\n"
            + f"\tBEGIN SELECT RAISE(ABORT, {quote(_mismatch_message)}); END;",
            f"CREATE TRIGGER {quote(self.name + '_nodelete')} BEFORE DELETE ON {quote(self.name)} "
            + 'BEGIN SELECT RAISE(ABORT, "deletion not allowed"); END;',
        )

    @property
    @cache
    def insert_sql(self) -> str:
        """The SQL statement to insert a row into the database."""
        vals = ['?']*(len(self.columns))
        pki = self.prikey_col_idx
        if self.prikey_is_datetime:
            vals[pki] = "CAST(STRFTIME('%s',?) AS INTEGER)"
        return f"INSERT INTO {quote(self.name)} ({','.join([quote(col.name) for col in self.columns])})\n" \
            + f"\tVALUES ({','.join(vals)})\n" \
            + f"\tON CONFLICT ({quote(self.columns[pki].name)}) DO UPDATE SET " \
            + ", ".join([ f"{quote(col.name)}=EXCLUDED.{quote(col.name)}"
                          for i, col in enumerate(self.columns) if i != pki ]) + ";"

    @property
    @cache
    def select_sql(self) -> str:
        """The SQL statement for a basic ``SELECT``."""
        cols :list[str] = [quote(col.name) for col in self.columns]
        if self.prikey_is_datetime:
            pki = self.prikey_col_idx
            cols[pki] = f"STRFTIME(\"%Y-%m-%d %H:%M:%SZ\",{cols[pki]},'unixepoch') AS {cols[pki]}"
        return f"SELECT {', '.join(cols)} FROM {quote(self.name)}"

    @property
    @cache
    def where_pk_sql(self) -> str:
        """A ``WHERE`` clause that references the primary key."""
        return f"WHERE {quote(self.columns[self.prikey_col_idx].name)}=" \
            + ( "CAST(STRFTIME('%s',?) AS INTEGER)" if self.prikey_is_datetime else "?" )

    @property
    @cache
    def order_pk_sql(self) -> str:
        """An ``ORDER BY ... ASC`` clause that sorts on the primary key."""
        return f"ORDER BY {quote(self.columns[self.prikey_col_idx].name)} ASC"

class RowMismatchError(RuntimeError):
    """An error thrown by :class:`InsertHelper` when a primary key already exists in the database but the
    columns other than the primary key don't match."""
    def __init__(self, prikey, existingrow :Sequence, insertrow :Sequence):
        self.prikey = prikey
        self.existingrow = existingrow
        self.insertrow = insertrow
        super().__init__(f"mismatch between existing database row and new row on primary key {prikey!r}")
    @property
    def rowdiff(self) -> str:
        """Creates a ``diff`` between the row in the database and the row whose ``INSERT`` failed."""
        import difflib
        import pprint
        diff = difflib.unified_diff(
            pprint.pformat(self.existingrow).splitlines(),
            pprint.pformat(self.insertrow).splitlines(),
            lineterm='', fromfile='existing_row', tofile='insert_row')
        return "\n".join(diff)

class InsertHelper(NamedTuple):
    """A helper for ``INSERT``-ing rows that converts an :exception:`~sqlite3.IntegrityError` into a :exception:`RowMismatchError` if applicable."""
    table :Table
    driver :DriverModule
    connection :CanExecute
    def insert(self, row :Sequence):
        pk = row[self.table.prikey_col_idx]
        if self.table.prikey_is_datetime:
            if not _sqlite_datetime_re.fullmatch(pk):
                raise ValueError(f"datetime primary key does not match recommended format 'YYYY-MM-DD HH:MM:SSZ'")
        try:
            self.connection.execute(self.table.insert_sql, row)
        except self.driver.dbapi2.IntegrityError as ex:
            if str(ex)!=_mismatch_message: raise ex
            with closing( self.connection.execute( self.table.select_sql + " " + self.table.where_pk_sql, (pk,) ) ) as cur:
                exrow = cur.fetchone()
            if not exrow: raise RuntimeError(f"internal error while handling exception: no rows for PK {pk !r} found")  # pragma: no cover
            # Note: this says it's correct to raise a different exception: https://stackoverflow.com/a/15344080
            raise RowMismatchError(prikey=pk, existingrow=exrow, insertrow=row) from ex

# noinspection PyPep8Naming
@contextmanager
def VaccuumHelper(dbfile :Filename, *, sqlite3mod :DriverModule, memvacuum :bool=False, vacuum :bool=False, sync :bool=True, verbose :bool=False):
    """A wrapper for a :class:`sqlite3.Connection` that provides some useful additions:

    ``PRAGMA foreign_keys`` will be turned on.

    :param dbfile: The filename of the SQLite3 database file, or the string ``":memory:"`` for an in-memory database.
    :param sqlite3mod: The ``sqlite3`` ``module`` - this is usually either :module:`sqlite3` or :module:`pysqlite3`.
    :param memvacuum: The database will be opened in memory first, and when you return from the context manager,
        the database will be ``VACUUM INTO``-ed into the given database file (which may not already exist and may
        not be ``":memory:"``).
        This is useful if you're building a database that fits into RAM; writing it out to disk after building it
        in RAM can be much faster (a drawback being that interrupting the process will cause the database to be lost).
        Cannot be used with :param:`vacuum`. For more information see https://www.sqlite.org/lang_vacuum.html
    :param vacuum: When you return from the context manager, a ``VACUUM`` command is executed.
        If you turned ``PRAGMA synchronous`` off with the :param:`sync` option, it will be turned back on first.
        Cannot be used with :param:`memvacuum`.
    :param sync: If you set this to ``False``, ``PRAGMA synchronous`` will be turned off.
    :param verbose: If you set this to ``True``, informational messages will be :func:`print`-ed on vacuuming.
    """
    if memvacuum:
        if vacuum: raise ValueError("cannot use memvacuum with vacuum")
        if dbfile==':memory:': raise ValueError("vacuum into memory does not make sense")
        elif os.path.exists(dbfile): raise FileExistsError(f"{dbfile!r}")  # fail early, before doing work
    with closing( sqlite3mod.connect(':memory:' if memvacuum else dbfile) ) as con:
        if not sync: con.execute('PRAGMA synchronous=OFF;')
        con.execute('PRAGMA foreign_keys=ON;')
        # foreign_keys can be very important so double-check it
        with closing( con.execute('PRAGMA foreign_keys') ) as cur:
            foreign_keys = cur.fetchone()
        if not foreign_keys[0]:  # pragma: no cover
            raise RuntimeError("failed to set sqlite foreign_keys")
        try:
            yield con
        finally:
            if memvacuum:
                if verbose: print(f"Now vaccuuming sqlite3 DB from memory into {dbfile}")  # pragma: no cover
                # note testing shows this will refuse to overwrite existing files
                with con: con.execute('VACUUM INTO ?;', (dbfile,))
            elif vacuum:
                if verbose: print(f"Now vaccuuming sqlite3 DB in file {dbfile}")  # pragma: no cover
                if not sync: con.execute('PRAGMA synchronous=ON;')
                with con: con.execute('VACUUM;')
