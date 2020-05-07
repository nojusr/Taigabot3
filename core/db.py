# Load and interface with specified db.

import functools
import sqlite3
from pathlib import Path
from sqlite3 import Connection, Cursor, OperationalError
from threading import Lock
from typing import Any, List, Optional, Tuple, Union

lock = Lock()

users_columns: List[str] = ['nick', 'mask']
channel_columns: List[str] = ['channel', 'commandprefix']

Data = Tuple[Optional[str], ...]
DBResult = List[Data]
Return = Optional[DBResult]
Execute = Union[Exception, Cursor]


def ccache():
    """Is for clearing all the get_* caches."""
    get_cell.cache_clear()
    get_row.cache_clear()
    get_column.cache_clear()
    get_column_names.cache_clear()
    get_table.cache_clear()
    get_table_names.cache_clear()
    add_column.cache_clear()


def add_channel(conn: Connection, channel: str, commandprefix: str) -> Return:
    """Is used to add specified channel to the database."""
    colnames: Optional[List[str]] = get_column_names(conn, 'channels')
    collen: int
    if not colnames:
        collen = 0
    else:
        collen = len(colnames)

    columns: Tuple[Optional[str], ...]
    global channel_columns
    if collen > len(channel_columns):
        filler = ['' for i in range((collen) - len(channel_columns))]
        columns = tuple([channel, commandprefix] + filler)
    else:
        columns = (channel, commandprefix)

    return set_row(conn, 'channels', columns)


def add_user(conn: Connection, nick: str, mask: str) -> Return:
    """Is used to add specified channel to the database."""
    colnames: Optional[List[str]] = get_column_names(conn, 'users')
    collen: int
    if not colnames:
        collen = 0
    else:
        collen = len(colnames)

    columns: Tuple[Optional[str], ...]
    global users_columns
    if collen > len(users_columns):
        filler = ['' for i in range((collen) - len(channel_columns))]
        columns = tuple([nick, mask] + filler)
    else:
        columns = (nick, mask)

    return set_row(conn, 'users', columns)


def connect(bot: Any, server: str) -> None:
    """Is used to connect to specified database."""
    if not bot.db_dir.exists():
        bot.db_dir.mkdir(parents=True)
    db_file: Path = bot.db_dir / (server + '.db')
    db: Connection = sqlite3.connect(
        db_file, timeout=1, check_same_thread=False)
    init_table(db, 'users', users_columns)
    init_table(db, 'channels', channel_columns)
    bot.dbs[server] = db


def init_table(conn: Connection, tablename: str, columns: List[str]) -> Return:
    """Is used to create a table using the inputed name and columns."""
    cursor = conn.cursor()
    joined_columns: str = ', '.join(columns)
    sql: str = f'CREATE TABLE IF NOT EXISTS {tablename}({joined_columns})'
    with lock:
        result: Execute = execute(cursor, conn, sql)
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


@functools.lru_cache(maxsize=128)
def add_column(conn: Connection, table: str, column: str) -> Return:
    """Is used to add a column to a table."""
    cursor = conn.cursor()
    sql: str = f'ALTER TABLE {table} ADD COLUMN {column} "text"'
    with lock:
        result: Execute = execute(cursor, conn, sql)
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


def set_cell(conn: Connection, table: str, column: str, data: str,
             matchcolumn: str, matchvalue: str) -> Return:
    """IS used to add a cell to the database."""
    cursor = conn.cursor()
    sql: str = f'UPDATE {table} SET {column}=? WHERE {matchcolumn}=?'
    with lock:
        result: Execute = execute(cursor, conn, sql, (data, matchvalue, ))
    ccache()
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


def set_row(conn: Connection, table: str, data: Data) -> Return:
    """Is used to set a whole row in the database."""
    cursor = conn.cursor()
    values: str = ('?,' * len(data))[:-1]
    sql: str = f'INSERT INTO {table} VALUES({values})'
    with lock:
        result: Execute = execute(cursor, conn, sql, data)
    ccache()
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


@functools.lru_cache(maxsize=128)
def get_cell(conn: Connection, table: str, column: str, matchcolumn: str,
             matchvalue: str) -> Return:
    """Is used to get a cell from the database."""
    cursor = conn.cursor()
    sql: str = f'SELECT {column} FROM {table} WHERE {matchcolumn}=?'
    with lock:
        result: Execute = execute(cursor, conn, sql, (matchvalue, ))
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


@functools.lru_cache(maxsize=128)
def get_row(conn: Connection, table: str, matchcolumn: str,
            matchvalue: str) -> Return:
    """Is used to get a whole row from the database."""
    cursor = conn.cursor()
    sql: str = f'SELECT * FROM {table} WHERE {matchcolumn}=?'
    with lock:
        result: Execute = execute(cursor, conn, sql, (matchvalue, ))
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


@functools.lru_cache(maxsize=128)
def get_column(conn: Connection, table: str, column: str) -> Return:
    """Is used to get a whole column from the database."""
    cursor = conn.cursor()
    sql: str = f'SELECT {column} FROM {table}'
    with lock:
        result: Execute = execute(cursor, conn, sql)
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


@functools.lru_cache(maxsize=128)
def get_column_names(conn: Connection, table: str) -> Optional[List[str]]:
    """Is for getting a list of columns names from the table."""
    cursor = conn.cursor()
    sql: str = f'SELECT * FROM {table}'
    with lock:
        result: Execute = execute(cursor, conn, sql)
    if not isinstance(result, Exception):
        columns: List[str] = [col[0] for col in result.description]
        return columns
    else:
        return None


@functools.lru_cache(maxsize=128)
def get_table(conn: Connection, table: str) -> Return:
    """Is used to get a whole table from the database."""
    cursor = conn.cursor()
    sql: str = f'SELECT * FROM {table}'
    with lock:
        result: Execute = execute(cursor, conn, sql)
    if isinstance(result, Exception):
        return None
    else:
        return result.fetchall()


@functools.lru_cache(maxsize=128)
def get_table_names(conn: Connection) -> Optional[List[str]]:
    """Is for getting a list of columns names from the table."""
    cursor = conn.cursor()
    sql: str = 'SELECT name FROM sqlite_master'
    with lock:
        result: Execute = execute(cursor, conn, sql)
    if not isinstance(result, Exception):
        tables: List[str] = [table[0] for table in result]
        return tables
    else:
        return None


def execute(cursor: Cursor,
            conn: Connection,
            sql: str,
            args: Optional[Tuple[Optional[str], ...]] = None) -> Execute:
    """Is used to execute an sql query on the database."""
    try:
        result: Execute
        if args is not None:
            result = cursor.execute(sql, args)
            conn.commit()
            return result
        result = cursor.execute(sql)
        conn.commit()
        return result
    except Exception as e:
        if type(e) == OperationalError:
            if 'duplicate' not in e.args[0]:
                print(f'Error in db.execute executing command: {e}.')
                if 'database is locked' in str(e):
                    conn.rollback()
        return e
