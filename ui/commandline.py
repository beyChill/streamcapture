import asyncio
from cmd import Cmd
from logging import getLogger
import os
from signal import SIGTERM
import sys
from time import sleep

import tabulate
from termcolor import colored

from app.sites.capture_streamer import CaptureStreamer
from app.sites.create_streamer import CreateStreamer
from app.sites.getstreamerurl import get_streamer_url
from app.utils.general_utils import recent_api_call
from app.utils.named_tuples import GetStreamerUrl
from ui.clivalidations import CliValidations
import app.database.dbactions as dbase

log = getLogger(__name__)


class Cli(Cmd, CliValidations):
    file = None
    intro = colored("Type help or ? for command infomation.\n", "cyan")
    user_prompt = "$"
    prompt = colored(f"{user_prompt}-> ", "green")

    def precmd(self, line):
        sys.stdout.flush()
        return line

    def default(self, line) -> None:
        line = line.split()
        self.stdout.write(f"Unknown command: {colored(line[0],'red')}\n")
        return None

    def do_prompt(self, new_prompt: str) -> None:
        if len(new_prompt)==0:
            return None
        
        self.change_prompt(new_prompt)
        self.user_prompt = new_prompt
        self.prompt = f"{colored(f'{self.user_prompt}-> ','green')}"

        return None

    def do_get(self, line) -> None:

        if None in (data := CliValidations().check_input(line, self.user_prompt)):
            return None

        streamer: GetStreamerUrl = asyncio.run(get_streamer_url([data.name_]))
        streamer = streamer[0]

        if not streamer.success:
            return None

        if recent_api_call():
            log.info(colored("Awaiting api rest cmd get", "yellow"))
            sleep(60)
            log.debug("resuming api call")

        # if not streamer.name_.strip():
        #     print(f"'get' action failed for {data.name_}")
        #     return None

        dbase.db_add_streamer(streamer.name_)

        if not None in (dbase.db_get_pid(streamer.name_)):
            log.info(
                f"Already capturing {colored(streamer.name_,"yellow")} from {data.site}"
            )
            return None

        if not streamer.url.strip():
            print("offline")
            return None

        if None in (
            streamer_data := [CreateStreamer(*x).return_data for x in [streamer]]
        ):
            return None

        [CaptureStreamer(x) for x in streamer_data]

        return None

    def do_block(self, line: str) -> None:
        name_, *rest = CliValidations().input(line)
        block_data = (name_, *rest)

        dbase.block_capture(block_data)

    def do_cap(self, line) -> None:

        if not (sort := CliValidations().check_table(line)):
            return None

        if not (query := dbase.db_capture(sort)):
            print("Presently capturing zero streamers")
            return None

        head = ["Streamers", "Capturing", "# Caps"]
        print(
            tabulate(
                query,
                headers=head,
                tablefmt="pretty",
                colalign=("left", "center", "center"),
            )
        )

    def do_offline(self, line) -> None:

        if not (sort := CliValidations().check_table(line)):
            return None

        if not (query := dbase.db_offline(sort)):
            print("Following zero streamers")
            return None

        head = ["Streamers", "Recent Stream", "# Caps"]
        print(
            tabulate(
                query,
                headers=head,
                tablefmt="pretty",
                colalign=("left", "center", "center"),
            )
        )

    def do_stop(self, line) -> None:
        if None in (data := CliValidations().check_input(line, self.user_prompt)):
            return None

        if None in (pid := dbase.db_get_pid(data.name_)):
            return None

        name_, pid = pid

        try:
            os.kill(pid, SIGTERM)
        except OSError as error:
            log.error(error)
        finally:
            dbase.stop_capturing(name_)

    def do_quit(self, _):
        sys.exit()

    def do_exit(self, _) -> None:
        self.do_quit(self)

    def do_end(self, _) -> None:
        self.do_quit(self)
