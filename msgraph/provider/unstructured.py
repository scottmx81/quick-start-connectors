import asyncio
import os
import aiohttp
import logging
import sys
import functools
from collections import OrderedDict


logger = logging.getLogger(__name__)

CACHE_LIMIT_BYTES = 20 * 1024 * 1024  # 20 MB to bytes


TIMEOUT_SECONDS = 3600

client_timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
client_session = None
unstructured = None


class UnstructuredRequestSession:
    def __init__(self, unstructured_base_url, api_key, session):
        self.get_content_url = f"{unstructured_base_url}/general/v0/general"
        self.headers = {"unstructured-api-key": api_key} if api_key else None
        self.session = session

        # Manually cache because functools.lru_cache does not support async methods
        self.cache = OrderedDict()

    def cache_size(self):
        # Calculate the total size of values in bytes
        total_size_bytes = functools.reduce(
             lambda a, b: a + b, map(lambda v: sys.getsizeof(v), self.cache.values()), 0
        )

        return total_size_bytes

    def cache_get(self, key):
        self.cache.move_to_end(key)

        return self.cache[key]

    def cache_put(self, key, item):
        self.cache[key] = item

        while self.cache_size() > CACHE_LIMIT_BYTES:
            self.cache.popitem()

    async def close_session(self):
        await self.session.close()

    async def get_unstructured_content(self, file):
        # Unpack tuple
        file_id, file_name, file_data = file

        # Check cache
        if file_id in self.cache:
            return self.cache_get(file_id)

        # Use FormData to pass in files parameter
        data = aiohttp.FormData()
        data.add_field("files", file_data, filename=file_name)
        print('get unstructured content')
        print(self.get_content_url)

        async with self.session.post(
            self.get_content_url,
            headers=self.headers,
            data=data,
        ) as response:
            print("got response from unstructured")
            content = await response.json()

            if not response.ok:
                logger.error(f"Error response from Unstructured: {content}")
                return None
            print('got unstructured response')

            self.cache_put(file_id, (file_name, content))

            return self.cache[file_id]

    async def gather(self, files):
        tasks = [self.get_unstructured_content(file) for file in files]
        return await asyncio.gather(*tasks)

    async def batch_get(self, files):
        print("Unstructured batch get")

        loop = asyncio.get_event_loop()
        results = await self.gather(files)

        print("Unstructured batch get got results")
        results = [result for result in results if result is not None]

        result_dict = {
         filename: content for filename, content in results if content is not None
        }
#
#         # Close session and loop
#         self.loop.run_until_complete(self.close_session())
#         self.close_loop()
#
        return result_dict


def get_unstructured_client():
    global unstructured
    global client_session

    if unstructured is not None:
        return unstructured

    if not client_session:
        loop = asyncio.get_event_loop()
        client_session = aiohttp.ClientSession(loop=loop, timeout=client_timeout)

    # Fetch environment variables
    assert (
        unstructured_base_url := os.environ.get("MSGRAPH_UNSTRUCTURED_BASE_URL")
    ), "MSGRAPH_UNSTRUCTURED_BASE_URL must be set"

    api_key = os.environ.get("MSGRAPH_UNSTRUCTURED_API_KEY")
    unstructured = UnstructuredRequestSession(unstructured_base_url, api_key, session=client_session)

    return unstructured
