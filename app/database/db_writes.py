import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from time import strftime
from typing import Any, Generator

from termcolor import colored

from app.config.settings import get_settings
from app.database.db_query import db_cap_status
from app.log.logger import init_logging
from app.utils.general_utils import display_pragma
from app.utils.named_tuples import DbFollowBlock, StreamerWithPid

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
init_logging()

config = get_settings()


@contextmanager
def connect():
    db_path = get_settings().DB_PATH
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
                PRAGMA cache_size=-5000;
                PRAGMA mmap_size = 300000000;
                PRAGMA temp_store = MEMORY;
                PRAGMA wal_autocheckpoint=500;
                PRAGMA page_size=5120;
                PRAGMA synchronous=OFF;
                """
        )
        if log.isEnabledFor(logging.DEBUG):
            display_pragma(conn)

        yield conn.cursor()


def _db_executemany(sql: str, values: list):
    write = None
    try:
        with connect() as cursor:
            if isinstance(values, list):
                write = cursor.executemany(sql, values)
            if not isinstance(values, list):
                write = cursor.execute(sql, values)
        return bool(write)
    except (sqlite3.Error) as error:
        print(error)
        log.error(error)


def _db_execute(sql: str, values):
    write = None
    try:
        with connect() as cursor:
            write = cursor.execute(sql, values)
        return bool(write)
    except sqlite3.Error as error:
        print(error)
        log.error(error)


def db_update_review(values: list):
    sql = "UPDATE chaturbate set review=? where streamer_name=?"
    _db_executemany(sql, values)


def db_update_last_broadcast(values: list):
    sql = "UPDATE chaturbate set last_broadcast=?, notes=? where streamer_name=?"
    _db_executemany(sql, values)


def db_update_pid(arg: StreamerWithPid):
    sql = "Update chaturbate SET recorded=recorded+1, pid=?, last_capture=?, last_broadcast=? WHERE streamer_name=?"
    args = (arg.pid, config.datetime, config.datetime, arg.streamer_name)
    if not _db_execute(sql, args):
        log.error(f"Failed to update {colored(arg.streamer_name, "red")}'s pid")
        return
    log.info(
        strftime("%H:%M:%S") + f": Capturing {colored(arg.streamer_name, "green")}"
    )


def db_remove_pid(value: int):
    sql = "UPDATE chaturbate SET pid=? WHERE pid=?"
    _db_execute(sql, (None, value))


def db_add_domain(name_: str, domain: str):
    sql = "INSERT INTO domains (streamer_name, domain) VALUES (?, ?)"
    args = (name_, domain)
    write = _db_execute(sql, args)
    if not write:
        log.error("Failed to add: %s", (colored(name_, "red")))


def db_add_streamer(name_: str, domain: str | None) -> tuple:
    today = datetime.now().replace(microsecond=0)
    sql = f"""
        INSERT INTO chaturbate (streamer_name, follow, detail_date, domain) 
        VALUES (?, ?, ?, ?) 
        ON CONFLICT (streamer_name) 
        DO UPDATE SET 
        detail_date=IFNULL(detail_date, '{today}'),
        follow='{today}',
        domain=EXCLUDED.domain
        WHERE follow IS NULL
        """
    args = (name_, today, today, domain)
    write = _db_execute(sql, args)
    query = db_cap_status(name_)

    if not write:
        log.error("Failed to add: %s", (colored(name_, "red")))

    return DbFollowBlock(bool(write), query)


def db_num_online(type_: str, data: int):
    sql = "INSERT INTO num_streamers (type_, num_) VALUES (?, ?)"
    args = (type_, data,)
    write = _db_execute(sql, args)
    if not write:
        log.error("Failed to add: %s", (colored("online streamers stat", "red")))
    return bool(write)


def stop_capturing(name_):
    sql = "UPDATE chaturbate SET follow=?, pid=? WHERE streamer_name=?"
    args = (None, None, name_)
    if not _db_execute(sql, args):
        log.error(colored(f"Unable to stop capture for {name_}", "red"))


def db_unfollow(name_):
    sql = "UPDATE chaturbate SET follow=? WHERE streamer_name=?"
    args = (None, name_)
    if not _db_execute(sql, args):
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
    if not _db_execute(sql, arg):
        log.error(colored("Block command failed", "red"))


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
    _db_executemany(sql, values)


