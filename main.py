from threading import Thread
from app.database.create_db import db_init
from app.log.logger import init_logging
from app.online_status import run_online_status
from app.ui.commandline import Cli


if __name__ == "__main__":
    init_logging()
    db_init()
    thread =Thread(target=run_online_status, daemon=True)
    thread.start()
    Cli().cmdloop()
