from cmd import Cmd
from logging import getLogger
import sys

from termcolor import colored


log = getLogger(__name__)


class Cli(Cmd):
    file = None
    intro = colored("Type help or ? for command infomation.\n", "cyan")
    user_prompt = "$"
    prompt = colored(f"{user_prompt}-> ", "green")

    def default(self, line):
        line =line.split()
        self.stdout.write(f"Unknown command: {colored(line[0],'red')}\n")

    def do_prompt(self, new_prompt:str) -> None:
        return None
    
    def do_get(self,line):
        return None
    
    def do_stop(self,line):
        return None
    
    def do_quit(self, _):
        sys.exit()

    def do_exit(self, _) -> None:
        self.do_quit(self)

    def do_end(self, _) -> None:
        self.do_quit(self)
    
