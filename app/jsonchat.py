import asyncio
from datetime import timedelta
from logging import getLogger
import math
import pandas as pd
from time import perf_counter, strftime
from httpx import AsyncClient
from random import choice, shuffle, uniform
from string import ascii_lowercase

from termcolor import colored

from app.database.dbactions import db_num_online, db_update_streamers
from app.utils.constants import HEADERS_JSON

log = getLogger(__name__)


def random_id(length) -> str:
    letters = ascii_lowercase
    return "".join(choice(letters) for _ in range(length)) + "a9a9ab8b8"


def removeDuplicates(list_):
    return list(set([i for i in list_]))


async def get_data(client: AsyncClient, url):
    data_columns: list = []

    response = await client.get(url, timeout=25)

    if response.status_code != 200:
        log.error(f"code: {response.status_code}, func: get_data")

        await asyncio.sleep(17)
        return [[random_id(10), 0, 0]]

    # Zero length element means url offset doesn't exist
    if len(response.json()["rooms"]) < 1:
        return [[random_id(10), 0, 0]]

    data_frame = pd.json_normalize(response.json(), "rooms")

    data_columns.append(
        data_frame[["username", "num_followers", "num_users"]].values.tolist()
    )

    data_brackets = sum(list(data_columns), [])
    return data_brackets


async def process_urls(i: int, num_batches: int, urls: list[str]) -> None:
    start_ = perf_counter()

    async with AsyncClient(headers=HEADERS_JSON, http2=True) as client:
        async with asyncio.TaskGroup() as group:
            results = []
            for url in urls:
                task = group.create_task(get_data(client, url))
                task.add_done_callback(lambda t: results.append(t.result()))

    remove_next = sum(list(results), [])
    list_to_tuple = [tuple(elem) for elem in remove_next]

    undupe = removeDuplicates(list_to_tuple)

    log.debug(
        f"Processed {colored(len(list_to_tuple),"green")} streamers in: {colored(round(perf_counter() - start_,4), 'green')} seconds"
    )

    # write to database
    db_num_online("batch", len(undupe))
    db_update_streamers(undupe)

    # delay to minimize triggering rate limit
    # sleep time can be adjusted up / down til limit (response code:429 occurs)
    # error on the side of caution when using a short delay.
    delay_ = uniform(109.05, 150.78)

    if num_batches > 2:
        delay_ = uniform(62.05, 120.78)

    _, minutes, seconds = str(timedelta(seconds=delay_)).split(":")
    seconds = round(float(seconds))
    log.debug(
        f"{strftime("%H:%M:%S")}: Next JSON batch process: {minutes}min {seconds}sec"
    )
    if i < (num_batches - 1):
        await asyncio.sleep(delay_)

    return None


async def get_num_online(base_url: str) -> int:
    offset = base_url + "0"
    async with AsyncClient(headers=HEADERS_JSON, http2=True) as client:
        response = await client.get(offset)
        if response.status_code != 200:
            return colored(f"-{response.status_code}", "red")

        #   cookie = response.cookies
        streamers_online: int = response.json()["total_count"]

    # save to database
    db_num_online("total", streamers_online)

    return streamers_online


def generate_urls(base_url: str, streamers_online: int) -> list[str]:
    json_urls: list[str] = []

    # range step based on Chaturbate standard of 90 streamers per url
    for i in range(0, streamers_online, 90):
        json_urls.append(base_url + f"{i}")

    # Sometimes the final predetermined url will no longer exist, causing a crash.
    # Process last url first, randomize the rest.
    json_urls.reverse()
    first_url = json_urls.pop(0)
    shuffle(json_urls)
    json_urls.insert(0, first_url)

    return json_urls


def url_grouping(json_urls: list[str]) -> list[list[str]]:
    # minimize chance for response code 429.
    rate_limit = 54
    count_urls = len(json_urls)

    if count_urls in range(55, 70):
        rate_limit = math.floor(len(json_urls) / 2)

    if count_urls in range(71, 86):
        rate_limit = math.floor(len(json_urls) / 2.5)

    url_groups = [
        json_urls[x : x + rate_limit] for x in range(1, len(json_urls), rate_limit)
    ]

    return url_groups


async def json_scraping() -> None:
    # data_columns: list = []
    base_url = (
        "https://chaturbate.com/api/ts/roomlist/room-list/?genders=f&limit=90&offset="
    )
    streamers_online = await get_num_online(base_url)

    log.info(
        f"{strftime("%H:%M:%S")}: {colored(streamers_online,"green")} streamers online"
    )

    json_urls = generate_urls(base_url, streamers_online)
    url_groups = url_grouping(json_urls)

    num_batches = len(url_groups)

    [await process_urls(i, num_batches, batch) for i, batch in enumerate(url_groups)]

    return None


def exception_handler(loop, context) -> None:
    log.error(context["exception"])
    log.error(context["message"])


async def query_streamers():
    await asyncio.sleep(57)
    while True:
        start = perf_counter()
        await json_scraping()

        log.debug(
            f"{strftime("%H:%M:%S")}: Processed JSONs in: {colored(round((perf_counter() - start), 3), "green")} seconds"
        )

        # Delay allows api rest between queries
        delay_ = uniform(601.05, 899.7)
        _, minutes, seconds = str(timedelta(seconds=delay_)).split(":")
        seconds = round(float(seconds))
        log.info(f"Next site query: {minutes}min {seconds}sec")
        await asyncio.sleep(delay_)


def run_query_json() -> None:
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(exception_handler)
    loop.create_task(query_streamers())
    loop.run_forever()


if __name__ == "__main__":
    run_query_json()
