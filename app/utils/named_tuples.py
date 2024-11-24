from pathlib import Path
from typing import Any, NamedTuple


class DbFollowBlock(NamedTuple):
    write: bool
    query: tuple[Any,Any,Any]


class HlsQueryResults(NamedTuple):
    name_: str
    success: bool = False
    url: str | None = None
    domain: str | None = None
    room_status: str = "offline"
    status_code: int = 200


class Streamer(NamedTuple):
    name_: str | None = None
    site_slug: str | None = None
    site: str | None = None


class StreamerData(NamedTuple):
    name_: str
    site: str
    url: str | None
    domain: str | None
    path_: Path
    file: str
    metadata: list
    success: bool


class StreamerWithPid(NamedTuple):
    pid: int
    streamer_name: str
    site_name: str
