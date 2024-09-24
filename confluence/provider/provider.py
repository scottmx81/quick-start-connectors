import logging

from .client import get_client

logger = logging.getLogger(__name__)


def search(query, access_token):
    client = get_client()
    pages = client.search(query, access_token)
    return pages
