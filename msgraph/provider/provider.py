import logging
import os

from flask import current_app as app
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from dotenv import load_dotenv

from .client import get_client
from .unstructured import get_unstructured_client


load_dotenv()

logger = logging.getLogger(__name__)


def search(query, access_token=None):
    client = get_client(access_token)
    search_response = client.search(query)
    return process_data_with_service(search_response, client)


def process_data_with_service(search_response, client):
    hits = collect_hits(search_response)
    items = collect_items(client, hits)
    process_items_with_unstructured(items)
    return serialize_results(items)


def collect_hits(search_response):
    hits = []

    for hit_container in search_response:
        hits.extend(hit_container.get("hits", []))

    return hits


def collect_items(graph_client, hits):
    items = []
    search_limit = app.config.get("SEARCH_LIMIT", 8)

    for hit in hits:
        if hit["resource"]["@odata.type"] == graph_client.DRIVE_ITEM_DATA_TYPE:
            parent_drive_id = hit["resource"]["parentReference"]["driveId"]
            resource_id = hit["resource"]["id"]

            if not is_usable_drive_item(hit):
                logger.info(f"Skipping {hit["resource"]["name"]}")
                continue

            logger.info(f"Found usable drive item: {hit["resource"]["name"]}")

            drive_item = graph_client.get_drive_item_content(
                parent_drive_id, resource_id
            )

            if drive_item:
                items.append({"hit": hit, "content": drive_item})

    return items[:search_limit]


def is_usable_drive_item(hit):
    unstructured_file_types = (
        os.environ.get("MSGRAPH_UNSTRUCTURED_FILE_TYPES").split(",")
        if os.environ.get("MSGRAPH_UNSTRUCTURED_FILE_TYPES")
        else []
    )

    passthrough_file_types = (
        os.environ.get("MSGRAPH_PASSTHROUGH_FILE_TYPES").split(",")
        if os.environ.get("MSGRAPH_PASSTHROUGH_FILE_TYPES")
        else []
    )

    _, file_extension = os.path.splitext(hit["resource"]["name"])

    if not file_extension:
        return False

    if file_extension not in unstructured_file_types and file_extension not in passthrough_file_types:
        return False

    return True


def process_items_with_unstructured(items):
    files = [
        (item["hit"]["resource"]["id"], item["hit"]["resource"]["name"], item["content"])
        for item in items
    ]
    for file in files:
        logger.info(f"Check with unstructured: {file[1]}")
    if len(files) > 0:
        logger.info("Found files.")
        #unstructured_client = get_unstructured_client()
        #unstructured_client.start_session()
        #unstructured_content = unstructured_client.batch_get(files)
        #unstructured_content = []
        pass


def serialize_results(items):
    results = []

    for item in items:
        serialized_item = serialize_item(item)

        if serialized_item:
            results.append(serialized_item)

    return results


def serialize_metadata(resource):
    data = {}

    # Only return primitive types, Coral cannot parse arrays/sub-dictionaries
    stripped_resource = {
        key: str(value)
        for key, value in resource.items()
        if isinstance(value, (str, int, bool))
    }
    data.update({**stripped_resource})

    if "name" in resource:
        data["title"] = resource["name"]

    if "webUrl" in resource:
        data["url"] = resource["webUrl"]

    return data


def serialize_item(item):
    _, file_extension = os.path.splitext(item["hit"]["resource"]["name"])

    if not file_extension:
        return None  # Ignore files without extensions

    passthrough_file_types = (
        os.environ.get("MSGRAPH_PASSTHROUGH_FILE_TYPES").split(",")
        if os.environ.get("MSGRAPH_PASSTHROUGH_FILE_TYPES")
        else []
    )

    data = {}

    if (resource := item["hit"].get("resource")) is not None:
        data = serialize_metadata(resource)

    if item["content"] is not None:
        try:
            data["text"] = item["content"].decode("utf-8")
        except:
            data["text"] = item["content"]

    return data
