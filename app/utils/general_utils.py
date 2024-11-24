from datetime import datetime, timedelta
from logging import getLogger
from app.database.db_query import db_get_api_time
from app.utils.constants import PRAGMA_QUERY

log = getLogger(__name__)


def recent_api_call():
    call = db_get_api_time()
    if None in call:
        return False
    time_compare = (datetime.now() - timedelta(seconds=100)) < (
        datetime.strptime(f"{call[0]}", "%Y-%m-%d %H:%M:%S")
    )
    return time_compare


def display_pragma(sqlite3_connect):

    for pragma in PRAGMA_QUERY:
        query = sqlite3_connect.execute(pragma)
        for value in query:
            print(pragma, "=", value[0])
