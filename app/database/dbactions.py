import os
import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from logging import getLogger
from time import strftime
from typing import Any, Dict
from datetime import date, datetime, timedelta
from termcolor import colored
from app.config.settings import get_settings
from app.utils.constants import DbAddStreamer, StreamerWithPid


log = getLogger(__name__)

config = get_settings()

DB_PATH = config.DB_PATH
DB_TABLES = config.DB_TABLES


@contextmanager
def connect() -> Generator[sqlite3.Cursor, Any, None]:
    with sqlite3.connect(DB_PATH) as connect:
        connect.executescript("PRAGMA synchronous=NORMAL;")
        yield connect.cursor()


@contextmanager
def db_init_connect() -> Generator[sqlite3.Cursor, Any, None]:
    with sqlite3.connect(DB_PATH) as connect:
        connect.executescript(
            """
            PRAGMA auto_vacuum=FULL;
            PRAGMA journal_mode=WAL;
            PRAGMA temp_store=MEMORY;
            PRAGMA synchronous=NORMAL;
            VACUUM;
            """
        )
        yield connect


def db_init() -> None:

    if not DB_PATH.exists():
        log.info(colored("Creating database folder", "cyan"))
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with db_init_connect() as cursor:
                with open(DB_TABLES, "r", encoding="utf-8") as file:
                    cursor.executescript(file.read())
                log.info(colored("Database inital setup complete", "cyan"))

        except sqlite3.OperationalError as error:
            log.error(error)

    log.info(colored("Database is ready", "cyan"))

    with connect() as cursor:
        cursor.executescript(
            """
            PRAGMA wal_autocheckpoint=500;
            PRAGMA temp_store=MEMORY;
            VACUUM;
            """
        )

    check_ghost_process()
    return None


# ***********************************
# * WRITE
# ***********************************


def db_update_review(values: list):
    sql = "UPDATE chaturbate set review=? where streamer_name=?"
    _db_executemany(sql, values)


def db_update_last_broadcast(values: list):
    sql = "UPDATE chaturbate set last_broadcast=?, notes=? where streamer_name=?"
    _db_executemany(sql, values)


def db_update_pid(arg: StreamerWithPid):
    sql = "Update chaturbate SET recorded=recorded+1, pid=?, last_capture=?, last_broadcast=? WHERE streamer_name=?"
    args = (arg.pid, config.datetime, config.datetime, arg.streamer_name)
    if not _write_to_db(sql, args):
        log.error(f"Failed to update {colored(arg.streamer_name, "red")}'s pid")
        return
    log.info(
        strftime("%H:%M:%S") + f": Capturing {colored(arg.streamer_name, "green")}"
    )


def db_remove_pid(value: int):
    sql = "UPDATE chaturbate SET pid=? WHERE pid=?"
    _db_execute(sql, (None, value))


def db_add_streamer(name_: str) -> tuple:
    today = datetime.now().replace(microsecond=0)
    sql = f"""
        INSERT INTO chaturbate (streamer_name, follow, detail_date) 
        VALUES (?, ?, ?) 
        ON CONFLICT (streamer_name) 
        DO UPDATE SET 
        detail_date=IFNULL(detail_date, '{today}'),
        follow='{today}' 
        WHERE follow IS NULL
        """
    args = (name_, today, today)
    write = _write_to_db(sql, args)
    query = db_cap_status(name_)

    if not write:
        log.error("Failed to add: %s", (colored(name_, "red")))
    return DbAddStreamer(bool(write), *query)


def db_num_online(type_: str, data: int):
    sql = "INSERT INTO num_streamers (type_, num_) VALUES (?, ?)"
    args = (
        type_,
        data,
    )
    write = _write_to_db(sql, args)
    if not write:
        log.error("Failed to add: %s", (colored("online streamers stat", "red")))
    return bool(write)


def stop_capturing(name_):
    sql = "UPDATE chaturbate SET follow=?, pid=? WHERE streamer_name=?"
    args = (None, None, name_)
    if not _write_to_db(sql, args):
        log.error(colored(f"Unable to stop capture for {name_}", "red"))


def db_unfollow(name_):
    sql = "UPDATE chaturbate SET follow=? WHERE streamer_name=?"
    args = (None, name_)
    if not _write_to_db(sql, args):
        log.error(colored(f"Unable to stop following {name_}", "red"))


def block_capture(data):
    name_, *reason = data
    reason = " ".join(reason)

    sql = """
        UPDATE chaturbate 
        SET block_date=?, follow=?, notes=IFNULL(notes, '')||?
        WHERE streamer_name=?
        """
    arg = (date.today(), None, f"{reason}", name_)
    if not _write_to_db(sql, arg):
        log.error(colored("Block command failed", "red"))


def _write_to_db(sql, arg) -> bool:

    try:
        with connect() as cursor:
            write = cursor.execute(sql, arg)

    except sqlite3.Error as error:
        print(error)
        log.error(error)
        write = None
    return bool(write)


def _write_to_db2(sql, arg) -> bool:
    try:
        with connect() as cursor:
            cursor.executescript(
                """
                PRAGMA mmap_size=268435456;
                PRAGMA page_size=8192;
                PRAGMA journal_mode = MEMORY;
                PRAGMA synchronous = OFF;
                """
            )
            write = cursor.execute(sql, arg)
    except sqlite3.Error as error:
        print(error)
        log.error(error)
        write = None
    return bool(write)


def db_update_streamers(values: list):
    sql = """
        INSERT INTO chaturbate (streamer_name, followers, viewers) 
        VALUES ( ?, ?, ?)
        ON CONFLICT (streamer_name)
        DO UPDATE SET 
        followers=EXCLUDED.followers,
        viewers=EXCLUDED.viewers, 
        last_broadcast=DATETIME('now', 'localtime'),
        detail_date=DATETIME('now', 'localtime'),
        most_viewers=MAX(most_viewers, EXCLUDED.viewers)
        """
    _db_executemany2(sql, values)


def _db_executemany(sql: str, values: list):
    write = None
    try:
        with connect() as cursor:
            if isinstance(values, list):
                write = cursor.executemany(sql, values)
            if not isinstance(values, list):
                write = cursor.execute(sql, values)
    except sqlite3.Error as error:
        log.error(error)
    finally:
        return bool(write)


def _db_executemany2(sql: str, values: list):
    write = None
    try:
        with connect() as cursor:
            cursor.executescript(
                """
                PRAGMA mmap_size=268435456;
                PRAGMA page_size=32768;
                PRAGMA synchronous=OFF;
                """
            )
            if isinstance(values, list):
                write = cursor.executemany(sql, values)
            if not isinstance(values, list):
                write = cursor.execute(sql, values)
    except sqlite3.Error as error:
        log.error(error)
    finally:
        return bool(write)


def _db_execute(sql: str, values: int):
    write = None
    try:
        with connect() as cursor:
            write = cursor.execute(sql, values)
    except sqlite3.Error as error:
        log.error(error)
    finally:
        return bool(write)


# ************************************
# * query
# ************************************


def fetchone(cursor) -> sqlite3.Cursor:
    return cursor.fetchone()


def fetchall(cursor) -> sqlite3.Cursor:
    return cursor.fetchall()


CURSOR_TYPE: Dict[str, Callable] = {
    "all": fetchall,
    "one": fetchone,
}


def query_db2(sql: str, action: str = "all"):
    try:
        with connect() as cursor:
            cursor.executescript(
                """
                PRAGMA synchronous=OFF;
                pragma page_size = 32768;
                PRAGMA mmap_size = 1000000000;
                """
            )
            if isinstance(sql, tuple):
                sql_query, args = sql
                cursor.execute(sql_query, args)
            if not isinstance(sql, tuple):
                cursor.execute(sql)

            data = CURSOR_TYPE[action](cursor)

    except sqlite3.Error as error:
        log.error(error)
        return None

    return data


def db_script(sql: str, action: str = "all"):
    try:
        with connect() as cursor:
            # cursor.executescript("""
            #     PRAGMA temp_store=MEMORY;
            #     PRAGMA synchronous=OFF;
            #     pragma page_size = 32768;
            #     """
            # )
            cursor.execute(sql)

            data = CURSOR_TYPE[action](cursor)

    except sqlite3.Error as error:
        log.error(error)
        return None

    return data


def db_get_api_time():
    sql = "SELECT max(query) from num_streamers"
    result = query_db2(sql, "one")
    return result


def db_get_all():
    sql = "SELECT streamer_name FROM chaturbate WHERE follow IS NOT NULL"
    result: list[str] = query_db2(sql, "all")
    return result


def db_cap_status(name_: str):
    sql = (
        "SELECT follow, block_date FROM chaturbate WHERE streamer_name=?",
        (name_,),
    )
    result: tuple[str | None, str | None] = query_db2(sql, "one")
    return result


def db_long_offline():
    value = date.today() - timedelta(days=100)
    sql = (
        """SELECT streamer_name 
        FROM chaturbate 
        WHERE last_broadcast<?
        AND (notes NOT LIKE "%archive%"
        OR notes IS NULL)
        AND block_date IS NULL ORDER BY RANDOM()
        LIMIT 30
        """,
        (value,),
    )
    result = query_db2(sql)
    data: list[str] = [f"{streamer_name}" for streamer_name, in result]

    return data


def db_followed():
    value = date.today() - timedelta(days=100)
    sql = (
        """SELECT streamer_name 
        FROM chaturbate 
        WHERE (last_broadcast>? or last_broadcast IS NULL) 
        AND follow IS NOT NULL AND pid IS NULL 
        AND block_date IS NULL ORDER BY RANDOM()
        """,
        (value,),
    )
    result = query_db2(sql)
    data: list[str] = [f"{streamer_name }" for streamer_name, in result]

    return data


def db_recorded(streamers: list):
    name_ = tuple(streamers)
    arg = f" IN {name_}"
    if len(streamers) < 2:
        arg = f"='{streamers[0]}'"

    sql = f"""
        SELECT streamer_name, recorded
        FROM chaturbate
        WHERE streamer_name{arg}
        """
    result: list[tuple[str, int]] = query_db2(sql)

    return result


def db_follow_offline(streamers: list):
    name_ = tuple(streamers)
    arg = f" IN {name_}"
    if len(streamers) < 2:
        arg = f"='{streamers[0]}'"

    sql = f"""
        SELECT streamer_name, last_broadcast, recorded
        FROM chaturbate
        WHERE streamer_name{arg}
        ORDER BY RANDOM()
        """
    result: list[tuple[str, int]] = query_db2(sql)

    return result


def db_get_pid(name_: str):
    sql = (
        "SELECT streamer_name, pid FROM chaturbate WHERE streamer_name=?",
        (name_,),
    )

    result: tuple[str, int | None] = query_db2(sql, "one")

    return result


def db_validate_pid():
    sql = "SELECT streamer_name, pid FROM chaturbate WHERE pid IS NOT NULL"

    result: list[tuple[str, int]] = query_db2(sql)

    return result


def db_all_pids():
    sql = "SELECT pid FROM chaturbate WHERE pid IS NOT NULL"

    result: list[tuple[int]] = query_db2(sql)

    return result


def db_capture(value):
    sql = f"SELECT streamer_name, follow, recorded FROM chaturbate WHERE pid IS NOT NULL ORDER BY {value}"

    result: list[tuple[str, str, int | None]] = query_db2(sql)

    return result


def db_offline(value):
    sql = f"""SELECT streamer_name, last_broadcast, recorded 
        FROM chaturbate 
        WHERE pid IS NULL AND follow IS NOT NULL AND block_date IS NULL 
        ORDER BY {value}"""

    result: list[tuple[str, str, int | None]] = query_db2(sql)

    return result


# ***********************************
# * general
# ***********************************


def check_ghost_process() -> None:
    """Delete inactive subprocess (pid) from database"""
    models_with_subprocess = db_validate_pid()

    if len(models_with_subprocess) == 0:
        return None

    log.info(colored("Validating previous capture activity", "cyan"))

    for name_, pid in models_with_subprocess:

        if pid is not None:
            try:
                os.kill(pid, 0)
            except OSError:
                db_remove_pid(pid)
                log.debug("Clearing inactive status for %s", name_)
