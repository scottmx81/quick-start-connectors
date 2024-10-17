import os
import json
import logging
from base64 import b64encode
from urllib.parse import urlencode

import requests
from connexion.exceptions import Unauthorized
from flask import abort, current_app as app, request

from . import UpstreamProviderError, provider


logger = logging.getLogger(__name__)

AUTHORIZATION_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "


def get_access_token() -> str | None:
    authorization_header = request.headers.get(AUTHORIZATION_HEADER, "")
    if authorization_header.startswith(BEARER_PREFIX):
        return authorization_header.removeprefix(BEARER_PREFIX)
    return None


def search(body):
    logger.info('got search request')
    try:
        data = provider.search(body["query"], get_access_token())
    except UpstreamProviderError as error:
        logger.error(f"Upstream provider error: {error.message}")
        abort(502, error.message)
    except AssertionError as error:
        logger.error(f"msgraph config error: {error}")
        abort(502, f"msgraph config error: {error}")

    return {"results": data}, 200, {"X-Connector-Id": app.config.get("APP_ID")}


def apikey_auth(token):
    api_key = str(app.config.get("CONNECTOR_API_KEY", ""))
    if api_key != "" and token != api_key:
        raise Unauthorized()
    # successfully authenticated
    return {}
