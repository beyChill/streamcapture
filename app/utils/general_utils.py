from datetime import datetime, timedelta
from app.database.dbactions import db_get_api_time


def recent_api_call():
    call = db_get_api_time()
    if None in call:
        return False
    time_compare = (datetime.now() - timedelta(seconds=100)) < (
        datetime.strptime(call[0], "%Y-%m-%d %H:%M:%S")
    )
    return time_compare
