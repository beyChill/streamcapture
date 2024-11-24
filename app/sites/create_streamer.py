from dataclasses import dataclass, field
from datetime import date, datetime
from logging import getLogger
from pathlib import Path
from time import strftime
from termcolor import colored
from app.config.settings import get_settings


from collections.abc import Callable

from app.database.db_writes import db_add_streamer
from app.utils.named_tuples import StreamerData


log = getLogger(__name__)
config = get_settings()


@dataclass(slots=True)
class FileSvs:

    @classmethod
    def set_video_path(cls, name_, site, dir=config.VIDEO_DIR) -> Path:
        save_dir = Path(dir, site, name_).joinpath()
        return save_dir

    def set_filename(self, name_: str, slug: str) -> str:
        now = datetime.now()
        slug = slug.upper()
        return f'{name_} [{slug}] {str(now.strftime("(%Y-%m-%d) %H%M%S"))}.mkv'


@dataclass(slots=True, eq=False)
class CreateStreamer(FileSvs):
    name_: str
    success: bool
    url: str | None
    domain: str | None
    room_status: str
    status_code: int
    site_slug: str = field(init=False, default="CB")
    site_name: str = field(init=False, default="Chaturbate")
    path_: Path = field(init=False)
    filename: str = field(init=False)
    file_svs: Callable = field(init=False)
    metadata: list = field(init=False)
    return_data: StreamerData = field(init=False)

    def __post_init__(self) -> StreamerData | None:

        # self.file_svs = filesvs()

        if not bool(self.success):
            log.error(f"{self.name_} is not a {self.site_name} streamer")
            return self.return_streamer()

        db_add_streamer(self.name_, self.domain)

        if not bool(self.url) and self.status_code == 200:
            log.info(
                colored(
                    f"{strftime("%H:%M:%S")}: {self.name_} is {self.room_status}",
                    "yellow",
                )
            )

        self.path_ = self.set_video_path(self.name_, self.site_name)
        self.filename = self.set_filename(self.name_, self.site_slug)
        self.metadata = self.set_metadata(self.name_, self.site_name)
        self.return_data = StreamerData(
            self.name_,
            self.site_name,
            self.url,
            self.domain,
            self.path_,
            self.filename,
            self.metadata,
            self.success,
        )

        del self

    def set_metadata(self, name_, site) -> list:
        metadata = []
        today_ = date.today()
        today_str = str(today_)

        meta = {
            "title": f"{name_} Live - {today_str}",
            "author": f"{name_}",
            "album_artist": f"{name_}",
            "publisher": f"{site}",
            "description": f"{name_} live cam performance on {today_}",
            "genre": "webcam",
            "copyright": "Creative Commons",
            "album": f"{name_} {site}",
            "date": f"{today_}",
            "year": f"{today_str}",
            "service_provider": "python3",
            "encoder": "x265",
        }

        # format for ffmpeg use
        for key, value in meta.items():
            metadata.extend(["-metadata", f"{key}={value}"])
        return metadata

    def return_streamer(self):
        return self.return_data
