import os
import requests

from msal import ConfidentialClientApplication
from flask import current_app as app

from .exceptions import UpstreamProviderError

AUTHORIZATION_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "


class GraphClient:
    DEFAULT_SCOPES = ["https://graph.microsoft.com/.default"]
    DEFAULT_REGION = "NAM"
    BASE_URL = "https://graph.microsoft.com/v1.0"
    SEARCH_ENTITY_TYPES = ["driveItem"]
    DRIVE_ITEM_DATA_TYPE = "#microsoft.graph.driveItem"
    SERVICE_AUTH = "service_auth"
    OAUTH = "oauth"

    def __init__(self, auth_type, search_limit):
        self.access_token = None
        self.user = None
        self.auth_type = auth_type
        self.search_limit = search_limit

    def get_auth_type(self):
        return self.auth_type

    def set_app_access_token(self, tenant_id, client_id, client_secret):
        try:
            credential = ConfidentialClientApplication(
                client_id=client_id,
                client_credential=client_secret,
                authority=f"https://login.microsoftonline.com/{tenant_id}",
            )

            token_response = credential.acquire_token_for_client(
                scopes=self.DEFAULT_SCOPES,
            )
            if "access_token" not in token_response:
                raise UpstreamProviderError(
                    "Error while retrieving access token from Microsoft Graph API"
                )
            self.access_token = token_response["access_token"]
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
        except Exception as e:
            raise UpstreamProviderError(
                f"Error while initializing MS Graph client: {str(e)}"
            )

    def set_user_access_token(self, token):
        self.access_token = token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def search(self, query):
        request = {
            "entityTypes": self.SEARCH_ENTITY_TYPES,
            "query": {
                "queryString": query,
                "size": self.search_limit,
            },
        }

        if self.auth_type == self.SERVICE_AUTH:
            request["region"] = self.DEFAULT_REGION

        response = requests.post(
            f"{self.BASE_URL}/search/query",
            headers=self.headers,
            json={"requests": [request]},
        )

        if not response.ok:
            raise UpstreamProviderError(
                f"Error while searching MS Graph API: {response.text}"
            )

        return response.json()["value"][0]["hitsContainers"]

    def get_drive_item_content(self, parent_drive_id, resource_id):
        response = requests.get(
            f"{self.BASE_URL}/drives/{parent_drive_id}/items/{resource_id}/content",
            headers=self.headers,
        )

        # Fail gracefully when retrieving content
        if not response.ok:
            return {}

        return response.content


def get_client(access_token=None):
    auth_type = os.environ.get("AUTH_TYPE")

    if auth_type:
        assert auth_type in [GraphClient.SERVICE_AUTH, GraphClient.OAUTH], "Invalid MSGRAPH_AUTH_TYPE value"
    else:
        auth_type = GraphClient.OAUTH

    search_limit = os.environ.get("SEARCH_LIMIT", 5)
    client = GraphClient(auth_type, search_limit)

    if auth_type == client.SERVICE_AUTH:
        assert (
            tenant_id := os.environ.get("MSGRAPH_TENANT_ID")
        ), "MSGRAPH_TENANT_ID must be set"
        assert (
            client_id := os.environ.get("MSGRAPH_CLIENT_ID")
        ), "MSGRAPH_CLIENT_ID must be set"
        assert (
            client_secret := os.environ.get("MSGRAPH_CLIENT_SECRET")
        ), "MSGRAPH_CLIENT_SECRET must be set"
        client.set_app_access_token(tenant_id, client_id, client_secret)
    elif auth_type == GraphClient.OAUTH:
        if access_token is None:
            raise UpstreamProviderError("No access token provided in request")
        client.set_user_access_token(access_token)
    else:
        raise UpstreamProviderError(f"Invalid auth type: {auth_type}")

    return client
