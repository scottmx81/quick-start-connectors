import logging
import os

import requests
from flask import current_app as app

from . import UpstreamProviderError


logger = logging.getLogger(__name__)

GRAPH_TENANT_ID = os.environ.get("GRAPH_TENANT_ID")
GRAPH_CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID")
GRAPH_CLIENT_SECRET = os.environ.get("GRAPH_CLIENT_SECRET")

cached_pages = {}
token = None


def search(query, is_retry=False):
    if not token:
        refresh_token()

    search_url = "https://graph.microsoft.com/v1.0/search/query"
    response = requests.post(
        search_url,
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "requests": [
                {
                    "entityTypes": ["message"],
                    "query": {"queryString": query},
                    "from": 0,
                    "size": 25,
                }
            ]
        },
    )

    data = []

    if not response.ok:
        if response.status_code == 401 and not is_retry:
            refresh_token()
            search(query, is_retry=True)
        try:
            message = response.json()["error"]["message"]
        except:
            message = "Error calling Microsoft Graph API"
        raise UpstreamProviderError(message)

    for hit_container in response.json()["value"][0]["hitsContainers"]:
        if hit_container["total"]:
            for hit in hit_container["hits"]:
                if hit["resource"]["@odata.type"] == "#microsoft.graph.message":
                        params = {
                            "$filter": f"internetMessageId eq '{hit['resource']['internetMessageId']}'",
                        }
                        body_response = requests.get(
                            f"https://graph.microsoft.com/v1.0/me/messages",
                            params=params,
                            headers={"Authorization": f"Bearer {token['access_token']}"}
                        )
                        if body_response.ok:
                            matching_messages = body_response.json()["value"]
                            if matching_messages:
                                data.extend(matching_messages)
                        else:
                            logger.error("Could not fetch message body")
    return data


def refresh_token():
    global token
    tenant = app.config["GRAPH_TENANT_ID"]
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "client_id": app.config["GRAPH_CLIENT_ID"],
        "client_secret": app.config["GRAPH_CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"] if token else app.config["CREDENTIAL"]["refresh_token"],
        "scope": "https://graph.microsoft.com/.default",
    }
    response = requests.post(url, data)

    if not response.ok:
        raise UpstreamProviderError("Error refreshing token")

    token = response.json()
