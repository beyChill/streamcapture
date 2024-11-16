

class CliValidations:

    site_slug: str
    site_name: str

    def input(self, line: str) -> None:
        if not bool(line.split()):
            raise CliErrors("", "input", "get candy cb")
        return line.split()