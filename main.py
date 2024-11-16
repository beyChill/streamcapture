from app.log.logger import init_logging
from ui.commandline import Cli


if __name__ =="__main__":
    init_logging()

    Cli().cmdloop()