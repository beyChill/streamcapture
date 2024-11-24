import logging
import os
import sqlite3
from contextlib import contextmanager
from termcolor import colored
from app.config.settings import get_settings
from app.database.db_query import db_validate_pid
from app.database.db_writes import db_remove_pid
from app.utils.general_utils import display_pragma


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
config = get_settings()


DB_PATH = config.DB_PATH
DB_TABLES = config.DB_TABLES
prag = [
    "PRAGMA auto_vacuum",
    "PRAGMA journal_mode",
    "PRAGMA temp_store",
    "PRAGMA synchronous",
    "PRAGMA wal_autocheckpoint",
    "PRAGMA cache_size",
    "PRAGMA page_size",
    "PRAGMA mmap_size",
    "PRAGMA cache_spill",
]


@contextmanager
def db_init_connect():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            PRAGMA mmap_size = 300000000;
            PRAGMA journal_mode=WAL;
            PRAGMA temp_store=MEMORY;
            PRAGMA synchronous=NORMAL;
            PRAGMA cache_size=-100000;
            """
        )

        yield conn


def db_init() -> None:
    prag_optimize = "pragma integrity_check; PRAGMA optimize; ANALYZE; VACUUM;"

    # setup database
    if not DB_PATH.exists():
        log.info(colored("Creating database folder", "cyan"))
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with db_init_connect() as conn:
                with open(DB_TABLES, "r", encoding="utf-8") as file:
                    conn.executescript(file.read())
                log.info(colored("Database inital setup complete", "cyan"))

        except sqlite3.OperationalError as error:
            log.error(error)

    log.info(colored("Database is ready", "cyan"))

    # database already setup
    with db_init_connect() as conn:
        conn.executescript(
            """
            PRAGMA wal_autocheckpoint=500;
            PRAGMA temp_store=MEMORY;
            PRAGMA mmap_size=268435456
            """
        )
        if log.isEnabledFor(logging.DEBUG):
            display_pragma(conn)

        conn.executescript(prag_optimize)

    check_ghost_process()
    return None


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

    return None
