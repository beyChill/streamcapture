import sqlite3
from contextlib import contextmanager
from logging import getLogger
from datetime import date, timedelta
from app.config.settings import get_settings


log = getLogger(__name__)


@contextmanager
def connect():
    db_path = get_settings().DB_PATH
    with sqlite3.connect(db_path) as conn:
        conn.executescript("PRAGMA synchronous=NORMAL;")

        yield conn.cursor()


def query_db2(sql: str | tuple, action: str = "all"):
    data = []
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

            if action == "all":
                data = cursor.fetchall()
            if action == "one":
                data = cursor.fetchone()

            return data

    except sqlite3.Error as error:
        log.error(error)
        return data


def db_get_api_time():
    sql = "SELECT max(query) from num_streamers"
    result = query_db2(sql, "one")
    return result


def db_get_all():
    sql = "SELECT streamer_name FROM chaturbate WHERE follow IS NOT NULL"
    result = query_db2(sql, "all")

    return result


def db_cap_status(name_: str):
    sql = (
        "SELECT follow, block_date,domain FROM chaturbate WHERE streamer_name=?",
        (name_,),
    )
    result = query_db2(sql, "one")
    follow, block, domain = result

    return (follow, block, domain)


def db_long_offline():
    value = date.today() - timedelta(days=100)
    sql = (
        """
        SELECT streamer_name 
        FROM chaturbate 
        WHERE last_broadcast<?
        AND (notes NOT LIKE "%archive%"
        OR notes IS NULL)
        AND block_date IS NULL ORDER BY RANDOM()
        LIMIT 30
        """,
        (value,),
    )
    if not (result := query_db2(sql)):
        data = [""]
        return data

    data: list[str] = [f"{streamer_name}" for streamer_name, in result]

    return data


def db_followed():
    value = date.today() - timedelta(days=100)
    sql = (
        """
        SELECT streamer_name 
        FROM chaturbate 
        WHERE (last_broadcast>? or last_broadcast IS NULL) 
        AND follow IS NOT NULL AND pid IS NULL 
        AND block_date IS NULL ORDER BY RANDOM()
        """,
        (value,),
    )
    if not (result := query_db2(sql)):
        data = [""]
        return data

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
    result = query_db2(sql)

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
    result = query_db2(sql)

    return result


def db_get_pid(name_: str):
    sql = (
        "SELECT streamer_name, pid FROM chaturbate WHERE streamer_name=?",
        (name_,),
    )
    result = query_db2(sql, "one")

    return result


def db_validate_pid():
    sql = "SELECT streamer_name, pid FROM chaturbate WHERE pid IS NOT NULL"
    result = query_db2(sql)

    return result


def db_all_pids():
    sql = "SELECT pid FROM chaturbate WHERE pid IS NOT NULL"
    result = query_db2(sql)

    return result


def db_capture(value):
    sql = f"SELECT streamer_name, follow, recorded FROM chaturbate WHERE pid IS NOT NULL ORDER BY {value}"
    result = query_db2(sql)

    return result


def db_offline(value):
    sql = f"""
        SELECT streamer_name, last_broadcast, recorded 
        FROM chaturbate 
        WHERE pid IS NULL AND follow IS NOT NULL AND block_date IS NULL 
        ORDER BY {value}
        """

    result = query_db2(sql)

    return result
