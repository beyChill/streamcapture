from dataclasses import dataclass, field
from time import strftime
from typing import Dict
from termcolor import colored


@dataclass(slots=True)
class GetDataError(Exception):
    name_: str
    key_: str
    code: int
    loader: str
    pre_text: str = field(init=False)
    error_dict: Dict[str, str] = field(init=False)

    def __post_init__(self):
        self.pre_text = f"{colored("[FAIL]",'red')} {strftime("%H:%M:%S")}: (http code: {self.code}) module: {self.loader} \n\t"
        self.error_dict = {
            "429": f"Chaturbate {colored('API overan','red')} with too many request",
            "not200": f"Unable to retrieve stream data for {colored(self.name_,'red')}",
            "notfound": f"{colored(self.name_,'red')} is not a Chaturbate Streamer",
        }

    def __str__(self):
        error: str = self.error_dict.get(
            self.key_, colored("An unexpected error has occured", "red")
        )
        return self.pre_text + error


@dataclass(slots=True)
class CliErrors(Exception):
    name_: str | None
    key_: str
    hint: str
    pre_text: str = field(init=False)
    error_dict: Dict = field(init=False)

    def __post_init__(self):
        self.pre_text = (
            f"{colored("[FAIL]" ,'red')} {strftime("%H:%M:%S")}: {self.hint} \n\t"
        )
        self.error_dict = {
            "input": f"Command missing {colored('model name','red')} and {colored('site abbreviation','red')}",
            "valid_chars": f"Model's name, {colored(self.name_, 'red')} contains invalid characters",
            "site_prompt": f"Unknown streaming site: {colored(self.name_,'red')}",
            "no_site": f"add {colored('streamer site', 'red')} to command",
            "chars_site": f"Only use alpha characters for site,{colored({self.name_},'red')}",
            "input_table": "The sort option is flawed.",
        }

    def __str__(self):
        error: str = self.error_dict.get(
            self.key_, colored("An unexpected error has occured", "red")
        )
        return self.pre_text + error
