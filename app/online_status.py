import asyncio
from collections.abc import Iterable
from datetime import timedelta
from logging import getLogger
from random import uniform
from time import perf_counter, strftime
from httpx import AsyncClient
from tabulate import tabulate
from termcolor import colored
from app.database.dbactions import db_follow_offline, db_followed, db_recorded
from app.sites.capture_streamer import CaptureStreamer
from app.sites.create_streamer import CreateStreamer
from app.sites.getstreamerurl import get_streamer_url
from app.utils.constants import HEADERS_IMG
from app.utils.general_utils import recent_api_call

log = getLogger(__name__)


class PrintTables:
    has_shown: bool = False


def streamer_grouping(followed: list):
    # Place streamers into query groups to present a
    # more typical query to cam site
    # Using 90 to match Chaturbate's 90 streamers per page.
    # caution is best approach to avoid 429s.
    group_limit = 90

    streamer_groups = [
        followed[x : x + group_limit] for x in range(0, len(followed), group_limit)
    ]
    return streamer_groups


async def get_data(client: AsyncClient, name_: str) -> tuple[int, str]:
    headers = {"path": f"/stream?room={name_}"}

    response = await client.get(
        f"https://jpeg.live.mmcdn.com/stream?room={name_}",
        headers=headers,
        timeout=9,
    )

    return (response.status_code, name_)


async def process_streamers(streamer_groups: list):
    start_ = perf_counter()

    async with AsyncClient(headers=HEADERS_IMG, http2=True) as client:
        async with asyncio.TaskGroup() as group:
            results = []

            for _, streamers in enumerate(streamer_groups):
                for streamer in streamers:
                    task = group.create_task(get_data(client, streamer))
                    task.add_done_callback(lambda t: results.append(t.result()))

    log.debug(
        f"Status for {colored(len(results), "green")} streamer(s) in: {colored(round(perf_counter() - start_, 4), 'green')} seconds"
    )

    return results


def sort_streamers(is_online: list[tuple[int, str]]):
    online: list = []
    offline: list = []

    for results in is_online:
        status_code, name_ = results
        if status_code == 200:
            online.append((name_))
        if status_code >= 201:
            offline.append((name_))

    return (online, offline)


def online_tables(online):
    # CLI table
    if len(online) <= 0:
        return None

    active_streamers = db_recorded(online)

    active_streamers.sort(key=lambda tup: tup[1], reverse=True)

    print(f"Followed streamers online: {colored(len(active_streamers),'green')}")
    head = ["Streamers", "# Caps"]
    print(
        tabulate(
            active_streamers,
            headers=head,
            tablefmt="pretty",
            colalign=("left", "center"),
        )
    )
    print()


def offline_tables(offline):
    if len(offline) <= 0:
        return None

    offline_streamers = db_follow_offline(offline)

    table_title = (
        f"Followed streamers offline: {colored(len(offline_streamers),'green')}"
    )

    if len(offline_streamers) > 10:
        table_title = f"Status for 10 of {len(offline_streamers)} followed streamers"
        offline_streamers = offline_streamers[:10]

    offline_streamers.sort(key=lambda tup: tup[1], reverse=False)
    print(table_title)
    head = ["Streamers", "Last Seen", "# Caps"]
    print(
        tabulate(
            offline_streamers,
            headers=head,
            tablefmt="pretty",
            colalign=("left", "left", "center"),
        )
    )
    print()


async def get_online_streamers() -> None:

    if (followed := db_followed()) == []:
        log.info(colored("Zero streamers are designated for capture", "yellow"))
        return None

    streamer_groups = streamer_grouping(followed)

    if recent_api_call():
        log.info(
            f"{strftime("%H:%M:%S")}: {colored("Awaiting api rest online_status",'yellow')}"
        )
        await asyncio.sleep(90)
        log.info(f"{strftime("%H:%M:%S")}: resuming api call")

    is_online = await process_streamers(streamer_groups)
    online, offline = sort_streamers(is_online)

    if not bool(PrintTables.has_shown):
        offline_tables(offline)
        online_tables(online)

    PrintTables.has_shown = True

    if len(online) > 0:
        streamer_wUrl = await get_streamer_url(online)
        cap_streamers = [CreateStreamer(*x).return_data for x in streamer_wUrl]

        [CaptureStreamer(x) for x in cap_streamers if isinstance(x, Iterable)]

    return None


async def query_online():

    while True:
        start = perf_counter()
        await get_online_streamers()
        log.info(
            f"{strftime("%H:%M:%S")}: Streamer check completed: {colored(round((perf_counter() - start), 4), "green")} seconds"
        )

        delay_ = uniform(290.05, 345.7)
        _, minutes, seconds = str(timedelta(seconds=delay_)).split(":")
        seconds = round(float(seconds))
        log.info(f"Next streamer check: {minutes}min {seconds}sec")
        await asyncio.sleep(delay_)


def run_online_status():
    loop = asyncio.new_event_loop()
    loop.create_task(query_online())
    loop.run_forever()


if __name__ == "__main__":
    run_online_status()
