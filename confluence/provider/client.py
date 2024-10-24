import asyncio
import aiohttp
import base64
import functools
import logging
import re
import requests
import sys

from collections import OrderedDict
from flask import current_app as app

from . import UpstreamProviderError

logger = logging.getLogger(__name__)

client = None


class BaseConfluenceClient:
    # Page consts
    PAGE_TYPE = "type"
    PAGE_BODY_FORMAT = "storage"

    # Timeout for async requests
    TIMEOUT_SECONDS = 20

    # Cache size limit to reduce memory over time
    CACHE_LIMIT_BYTES = 20 * 1024 * 1024  # 20 MB to bytes

    def __init__(self, search_limit=10):
        self.search_limit = search_limit
        # Manually cache because functools.lru_cache does not support async methods
        self.cache = OrderedDict()
        self.loop = None

    def _cache_size(self):
        # Calculate the total size of values in bytes
        total_size_bytes = functools.reduce(
            lambda a, b: a + b, map(lambda v: sys.getsizeof(v), self.cache.values()), 0
        )

        return total_size_bytes

    def _cache_get(self, key):
        self.cache.move_to_end(key)

        return self.cache[key]

    def _cache_put(self, key, item):
        self.cache[key] = item

        while self._cache_size() > self.CACHE_LIMIT_BYTES:
            self.cache.popitem()

    def _start_session(self):
        self.loop = asyncio.new_event_loop()
        # Create ClientTimeout object to apply timeout for every request in the session
        client_timeout = aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
        self.session = aiohttp.ClientSession(loop=self.loop, timeout=client_timeout)

    async def _close_session(self):
        await self.session.close()

    def _close_session_and_loop(self):
        # Close session and loop, session closing must be done in an async method
        self.loop.run_until_complete(self._close_session())
        self.loop.stop()
        self.loop.close()

    async def _gather(self, pages, access_token=None):
        tasks = [
            self._get_page(page["id"], access_token)
            for page in pages
            if self.PAGE_TYPE in page
        ]

        return await asyncio.gather(*tasks)

    async def _get_page(self, page_id, access_token=None):
        # Check cache
        if page_id in self.cache:
            return self._cache_get(page_id)

        base_url = self._get_base_url(access_token)
        get_page_by_id_url = f"{base_url}/wiki/api/v2/pages/{page_id}"
        params = {"body-format": self.PAGE_BODY_FORMAT}

        async with self.session.get(
            get_page_by_id_url,
            headers=self._get_headers(access_token),
            params=params,
        ) as response:
            if not response.ok:
                logger.error(f"Error response from Confluence: {response.text}")
                return None

            content = await response.json()

            base_url = self._get_base_url(access_token)
            page_url = f"{base_url}/wiki{content['_links']['webui']}"

            serialized_page = {
                "title": content["title"],
                "text": content["body"][self.PAGE_BODY_FORMAT]["value"],
                "url": page_url,
            }

            # Update cache
            self._cache_put(page_id, serialized_page)
            return self._cache_get(page_id)

    def search_pages(self, query, access_token=None):
        base_url = self._get_base_url(access_token)
        search_url = f"{base_url}/wiki/rest/api/content/search"

        # Substitutes any sequence of non-alphanumeric or whitespace characters with a whitespace
        formatted_query = re.sub("\W+", " ", query)

        params = {
            "cql": f'text ~ "{formatted_query}"',
            "limit": self.search_limit,
        }

        response = requests.get(
            search_url,
            headers=self._get_headers(access_token),
            params=params,
        )

        if response.status_code != 200:
            raise UpstreamProviderError(
                f"Error during Confluence search: {response.text}"
            )

        return response.json().get("results", [])

    def fetch_pages(self, pages, access_token: str | None = None):
        self._start_session()
        results = self.loop.run_until_complete(self._gather(pages, access_token))
        self._close_session_and_loop()

        return results

    def search(self, query, access_token=None):
        pages = self.search_pages(query, access_token)

        return [
            page for page in self.fetch_pages(pages, access_token) if page is not None
        ]

    def _get_headers(self, access_token: str | None = None) -> dict[str, str]:
        raise NotImplementedError()

    def _get_base_url(self, access_token: str | None = None):
        raise NotImplementedError()


class ServiceAuthConfluenceClient(BaseConfluenceClient):
    def __init__(self, product_url, user, api_token, search_limit):
        self.product_url = product_url
        self.user = user
        self.api_token = api_token
        super().__init__(search_limit=search_limit)

    def _get_base_url(self, access_token: str | None = None):
        return self.product_url

    def _get_headers(self, access_token: str | None = None) -> dict[str, str]:
        credentials = f"{self.user}:{self.api_token}"
        credentials_encoded = base64.b64encode(credentials.encode()).decode("ascii")

        return {
            "Authorization": f"Basic {credentials_encoded}",
        }


class OAuthConfluenceClient(BaseConfluenceClient):
    # Cache for token to organization cloud id mappings
    org_ids: dict[str, str] = {}

    def _get_base_url(self, access_token: str | None = None):
        if not access_token:
            raise AssertionError(
                "Access token required to construct Confluence cloud URLs"
            )

        if access_token in self.org_ids:
            return (
                f"https://api.atlassian.com/ex/confluence/{self.org_ids[access_token]}"
            )

        response = requests.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers=self._get_headers(access_token),
        )

        if response.status_code != 200:
            logger.error("Error determining Confluence base URL")
            return

        accessible_resources = response.json()

        if not accessible_resources:
            logger.error("No resources available to user")
            return

        org_id = accessible_resources[0]["id"]
        self.org_ids[access_token] = org_id

        return f"https://api.atlassian.com/ex/confluence/{org_id}"

    def _get_headers(self, access_token: str | None = None) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
        }


def get_client():
    global client

    if client is None:
        auth_method = app.config.get("AUTH_METHOD", "oauth")
        assert auth_method in [
            "oauth",
            "service_auth",
        ], 'CONFLUENCE_AUTH_METHOD must be "oauth" or "service_auth"'

        try:
            search_limit = int(app.config.get("SEARCH_LIMIT", 10))
        except ValueError:
            raise ValueError("SEARCH_LIMIT must be an integer")

        if auth_method == "oauth":
            client = OAuthConfluenceClient()
        elif auth_method == "service_auth":
            assert (
                product_url := app.config.get("PRODUCT_URL")
            ), "CONFLUENCE_PRODUCT_URL must be set"
            assert (user := app.config.get("USER")), "CONFLUENCE_USER must be set"
            assert (
                api_token := app.config.get("API_TOKEN")
            ), "CONFLUENCE_API_TOKEN must be set"
            client = ServiceAuthConfluenceClient(
                product_url, user, api_token, search_limit
            )

    return client
