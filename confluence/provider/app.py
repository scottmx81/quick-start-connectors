import logging

from connexion.exceptions import Unauthorized
from flask import abort, request, current_app as app

from . import UpstreamProviderError, provider

logger = logging.getLogger(__name__)
AUTHORIZATION_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "


def search(body):
    logger.debug(f'Search request: {body["query"]}')

    try:
        data = provider.search(body["query"], get_access_token())
        logger.info(f"Found {len(data)} results")
    except UpstreamProviderError as error:
        logger.error(f"Upstream search error: {error.message}")
        abort(502, error.message)

    return {"results": data}, 200, {"X-Connector-Id": app.config.get("APP_ID")}


def get_access_token() -> str | None:
    authorization_header = request.headers.get(AUTHORIZATION_HEADER, "")
    if authorization_header.startswith(BEARER_PREFIX):
        return authorization_header.removeprefix(BEARER_PREFIX)
    return None


def apikey_auth(token):
    api_key = str(app.config.get("CONNECTOR_API_KEY", ""))
    if api_key != "" and token != api_key:
        raise Unauthorized()
    # successfully authenticated
    return {}
