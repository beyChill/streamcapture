from typing import NamedTuple, Optional

class GetStreamerUrl(NamedTuple):
    name_: str
    success: bool = False
    url: str = ""
    room_status: str = "offline"
    status_code: Optional[int] = 200

class Streamer(NamedTuple):
    name_: str
    site_slug: str
    site: str
