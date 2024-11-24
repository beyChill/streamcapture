import asyncio
from collections.abc import Iterable
import math
from random import choice
from string import ascii_lowercase, digits
import subprocess
from dataclasses import dataclass, field
from io import TextIOWrapper
from logging import DEBUG, INFO, getLogger
from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen
from threading import Thread
from time import sleep, strftime
from termcolor import colored
from app.database.db_query import db_cap_status
from app.database.db_writes import db_remove_pid, db_update_pid
from app.sites.create_streamer import CreateStreamer
from app.sites.getstreamerurl import get_streamer_url
from app.utils.general_utils import recent_api_call
from app.utils.named_tuples import HlsQueryResults, StreamerData, StreamerWithPid

log = getLogger(__name__)

log.setLevel(INFO)

@dataclass(
    slots=True,
    init=False,
    frozen=True,
    repr=False,
    eq=False,
)
class CaptureError(Exception):
    msg: str

    def __init__(self, msg) -> None:
        object.__setattr__(self, "msg", msg)


@dataclass(slots=True)
class CaptureStreamer:
    data: StreamerData
    metadata: list = field(init=False)
    path_: Path = field(init=False)
    file: Path = field(init=False)
    name_: str = field(init=False)
    site: str = field(init=False)
    url: str | None = field(init=False)
    args_ffmpeg: list = field(default_factory=list)
    pid: int = field(default=0, init=False)
    capture_time: int = field(default=55, init=False)
    process: Popen[bytes] = field(init=False)

    def __post_init__(self):

        self.create_path()
        self.metadata = self.data.metadata
        self.path_ = self.data.path_
        self.name_ = self.data.name_
        self.site = self.data.site
        self.url = self.data.url
        self.file = Path(self.data.path_, self.data.file).joinpath()
        self.args_ffmpeg = self.ffmpeg_args()
        if self.url:
            self.activate()

    def create_path(self):
        self.data.path_.mkdir(parents=True, exist_ok=True)

    def random_str(self) -> str:
        letters = f"{ascii_lowercase}{digits}"
        return "-sd-" + "".join(choice(letters) for _ in range(64)) + "_trns_h264"

    def generate_url(self, name_: str, domain: str):
        random_string = self.random_str()
        url = f"https://{domain}/live-hls/amlst:{name_}{random_string}/playlist.m3u8"
        return url

    def ffmpeg_args(self):
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-i",
            self.url,
            *self.metadata,
            "-t",
            f"{self.capture_time}",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            self.file,
        ]
        return args

    def std_out(self) -> int | TextIOWrapper:
        if log.isEnabledFor(DEBUG):
            return open(f"{self.path_}/stdout.log", "w+", encoding="utf-8")

        return PIPE

    def time_limit_reached(self, process: Popen):
        time_value: int = 0
        progress_value: str = ""
        if process.stdout is not None:
            for output in process.stdout:
                if "out_time_ms" in (line := output.strip()):
                    _, t = line.split("=")
                    time_value = int(t)

                if "end" in (line := output.strip()):
                    _, progress_value = line.split("=")

                if (
                    math.ceil(int(time_value) / 1e6) == self.capture_time
                    and progress_value == "end"
                ):
                    return True
        return False

    def subprocess_status(self, db_model: StreamerWithPid, process: Popen):
        pid, name_, site = db_model

        max_time: bool = False
        err = f"{strftime("%H:%M:%S")}: {colored(f"{name_} from {site} stopped", "yellow")}"
        try:
            while True:
                if process.poll() is not None:
                    print(err)
                    break

                max_time = self.time_limit_reached(process)
                if bool(max_time):
                    print(err)
                    print("max:", max_time)
                    break

            if recent_api_call():
                log.info(
                    f"{strftime("%H:%M:%S")}: {colored('Awaiting api rest capture_streamer','yellow')}"
                )
                sleep(90)
                log.info(
                    f"{strftime("%H:%M:%S")}: {colored('resuming api call','yellow')}"
                )

            sleep(9)

            follow, block, domain = db_cap_status(name_)

            if not bool(follow) or bool(block):
                db_remove_pid(pid)
                return None

            db_remove_pid(pid)

            data = [
                HlsQueryResults(
                    name_,
                    success=True,
                    url=self.generate_url(name_, domain),
                    domain=domain,
                )
            ]
            if not max_time:
                data = asyncio.run(get_streamer_url([name_]))
                print(":oops")

            re_streamer = [
                CreateStreamer(*x).return_data for x in data if isinstance(x, Iterable)
            ]

            _ = [CaptureStreamer(x) for x in re_streamer if isinstance(x, Iterable)]
        except CaptureError as e:
            log.info(e.msg)

    def activate(self):
        process = Popen(
            self.args_ffmpeg,
            stdin=DEVNULL,
            stdout=self.std_out(),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            encoding="utf8",
            universal_newlines=True,
        )
        pid = process.pid
        db_model = StreamerWithPid(pid, self.name_, self.site)

        db_update_pid(db_model)

        thread = Thread(
            target=self.subprocess_status, args=(db_model, process), daemon=True
        )
        thread.start()
        del self
