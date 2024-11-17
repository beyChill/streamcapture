import asyncio
from logging import getLogger
from time import perf_counter
from httpx import AsyncClient
from termcolor import colored
from app.errors.custom_errors import GetDataError
from app.utils.constants import HEADERS_STREAM_URL, GetStreamerUrl

log = getLogger(__name__)


async def get_streamer_url(streamers: list[str]):
    start_ = perf_counter()
    async with AsyncClient(headers=HEADERS_STREAM_URL, http2=True) as client:
        try:
            async with asyncio.TaskGroup() as group:
                results = []
                for name_ in streamers:
                    task = group.create_task(get_data(client, name_))
                    task.add_done_callback(lambda t: results.append(t.result()))
        except:
            pass
    log.debug(
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

    success:bool = True
    data_url:str =''
    try:
        if response.status_code == 429:
            raise GetDataError(name_, "429", response.status_code, __loader__.name)
        if response.status_code != 200:
            raise GetDataError(name_, "not200", response.status_code, __loader__.name)

        data = response.json()

        if not bool(data["success"]):
            success=False
            raise GetDataError(name_, "notfound", response.status_code, __loader__.name)
        
        success = data["success"]
        data_url=data['url']
    except GetDataError as e:
        print(e)
        return GetStreamerUrl(name_, success, data_url, "failed", response.status_code)

    return GetStreamerUrl(
        name_, success, data_url, data["room_status"], response.status_code
    )
