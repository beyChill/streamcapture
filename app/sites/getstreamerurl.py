import asyncio
from typing import Any
from urllib.parse import urlparse
from logging import getLogger
from time import perf_counter
from httpx import AsyncClient
from termcolor import colored
from app.errors.custom_errors import GetDataError
from app.utils.constants import HEADERS_STREAM_URL
from app.utils.named_tuples import HlsQueryResults


log = getLogger(__name__)


async def get_streamer_url(streamers: list[str]):
    start_ = perf_counter()
    results: list[HlsQueryResults] = []
    async with AsyncClient(headers=HEADERS_STREAM_URL, http2=True) as client:
        try:
            async with asyncio.TaskGroup() as group:
                for name_ in streamers:
                    task = group.create_task(get_data(client, name_))
                    task.add_done_callback(lambda t: results.append(t.result()))
        except asyncio.CancelledError:
            print("get_streamer_url():  was canceled")

    if len(streamers) > 1:
        log.info(
            f"Processed {colored(len(results),"green")} streamers in: {colored(round(perf_counter() - start_,4), 'green')} seconds"
        )

    return results


async def get_data(client: AsyncClient, name_: str):
    # functionName=inspect.getframeinfo(inspect.currentframe()).function

    base_url = "https://chaturbate.com/get_edge_hls_url_ajax/"
    params = {"room_slug": name_, "bandwidth": "high"}
    headers = {"Referer": f"https://chaturbate.com/{name_}/"}
    response = await client.post(
        base_url,
        headers=headers,
        data=params,
        timeout=15,
    )

    try:
        if response.status_code == 429:
            raise GetDataError(name_, "429", response.status_code, __loader__.name)
        if response.status_code != 200:
            raise GetDataError(name_, "not200", response.status_code, __loader__.name)

        data = response.json()

        if not bool(data["success"]):
            raise GetDataError(name_, "notfound", response.status_code, __loader__.name)

        success = data["success"]

        if not bool(data["url"]):
            return HlsQueryResults(name_, success, room_status=data["room_status"])

        data_url = data["url"]
        domain = urlparse(data_url).netloc

    except GetDataError as e:
        print(e)
        return HlsQueryResults(name_)

    return HlsQueryResults(
        name_, success, data_url, domain, data["room_status"], response.status_code
    )
