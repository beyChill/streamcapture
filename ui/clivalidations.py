from app.config.settings import get_settings
from app.errors.custom_errors import CliErrors
from app.utils.named_tuples import Streamer


class CliValidations:

    site_slug: str
    site_name: str
    lowercase: str = "abcdefghijklmnopqrstuvwxyz"
    uppercase: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    letters: str = f"{lowercase}{uppercase}"
    digits: str = "0123456789"
    default_prompt=config = get_settings().default_cli_prompt
    lowercase_digits: str = f"{lowercase}{digits}_"
    VALIDSITES: set[str] = {"cb", "mfc", "sc"}
    SORT_OPTIONS: dict[str, str] = {
        "name": "streamer_name",
        "date": "last_broadcast",
        "num": "recorded",
    }

    @classmethod
    def input(self, line: str)  -> list[str]:
        if not bool(line.split()):
            raise CliErrors("", "input", "get Kandy cb")
        return line.split()
    
    @classmethod
    def name_chars(cls, name_: str) -> None:
        if not all(chars in cls.lowercase_digits for chars in name_):
            raise CliErrors(
                name_, "valid_chars", "Valid characters are lowercase letters, digits 0-9, and underscore ( _ )"
            )

    @classmethod
    def change_prompt(self, prompt) -> None:
        try:
            if prompt not in self.VALIDSITES:
                raise CliErrors(prompt, "site_prompt", f"sites {self.VALIDSITES}")
        except  CliErrors as e:
            print(e)
        return None

    @classmethod
    def has_cam_site(self, prompt: str, rest: list) -> None:
        if prompt == self.default_prompt and not rest:
            raise CliErrors(None, "no_site", f"sites {self.VALIDSITES}")

    @classmethod
    def chk_prompt(self, prompt: str) -> None:
        if prompt == self.default_prompt:
            return None

        if prompt not in self.VALIDSITES:
            raise CliErrors(prompt, "chars_prompt", f"sites {self.VALIDSITES}")

        self.site_slug = prompt

    @classmethod
    def chk_user_prompt(self, prompt:str) -> None:
        if not bool(prompt):
            return None

        prompt, *_ = prompt

        if not bool(prompt):
            raise CliErrors(None, "no_site", f"sites {self.VALIDSITES}")

        if prompt not in self.VALIDSITES:
            raise CliErrors(prompt, "site_prompt", f"sites {self.VALIDSITES}")

        self.site_slug = prompt

    @classmethod
    def slug_to_site(self) -> None:
        self.site_name = self.SITENAME.get(self.site_slug)

    @classmethod
    def check_input(self, line: str, prompt:str) -> Streamer:
        try:
            print(line,type(line))

            name_, *rest = self.input(line)

            self.name_chars(name_)
            self.has_cam_site(prompt, rest)
            self.chk_prompt(prompt)
            self.chk_user_prompt(rest)
            self.slug_to_site()

            return Streamer(name_, self.site_slug, self.site_name)
        except CliErrors as e:
            print(e)
            return Streamer(None, None, None)
        
    @classmethod
    def check_sort(self, sort: str):
        if sort not in self.SORT_OPTIONS.keys():
            raise CliErrors("", "input_table", "num = number")

    def input_table(self, line: str):
        if not bool(line.split()):
            raise CliErrors("", "input_table", "num = number")
        return line.split()
    
    def check_table(self, line: str):
        try:
            sort, *_ = self.input_table(line)
            self.check_sort(sort)
            value = self.SORT_OPTIONS.get(sort)
            return value

        except CliErrors as e:
            print(e)
            return None
