import logging
import re

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from . import EXTENDED_STOPWORDS
from .client import get_client

logger = logging.getLogger(__name__)


def search(query):
    client = get_client()
    pages = client.search(build_cql(query, "AND"))

    if not pages:
        pages = client.search(build_cql(query, "OR"))

    return pages


def build_cql(query: str, operator) -> str:
    stripped_query = re.sub("\W+", " ", query)
    query_words = split_and_remove_stopwords(stripped_query)

    cql = ""

    for word in query_words:
        cql += f' {operator} text ~ "{word}"'

    return re.sub(f"^ {operator} ", "", cql)


def split_and_remove_stopwords(query: str):
    words = word_tokenize(query)
    stop_words = set(stopwords.words("english"))
    stop_words.update(EXTENDED_STOPWORDS)
    return [word for word in words if word.lower() not in stop_words]
