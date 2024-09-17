import logging
import re

import nltk
from nltk.corpus import wordnet

from .client import get_client

logger = logging.getLogger(__name__)


def search(query):
    client = get_client()
    pages = client.search(build_cql(query))
    return pages


def build_cql(query):
    stripped_query = re.sub("\W+", " ", query)
    tokens = nltk.word_tokenize(stripped_query)
    tagged_tokens = nltk.pos_tag(tokens)

    grammar = r"""
        NP: {<NNP><NNP>}    # Chunk sequences of proper nouns (e.g., New York)
            {<NN.*>+}       # Chunk any sequence of nouns (e.g., Boroughs)
    """

    chunk_parser = nltk.RegexpParser(grammar)
    tree = chunk_parser.parse(tagged_tokens)
    noun_phrases = []

    for subtree in tree.subtrees():
        if subtree.label() == "NP":
            phrase = " ".join(word for word, tag in subtree.leaves())
            noun_phrases.append(phrase)

    cql = ""

    for noun_phrase in noun_phrases:
        synonyms = get_synonyms(noun_phrase)

        if synonyms:
            cql += " OR ("
            cql_synonyms = []

            for synonym in synonyms:
                cql_synonyms.append(f'text ~ "{synonym}"')

            cql += " OR ".join(cql_synonyms)
            cql += ")"
        else:
            cql += f' OR text ~ "{noun_phrase}"'

    cql = re.sub("^ OR ", "", cql)

    return cql


def get_synonyms(word):
    synonyms = set()

    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name())

    return list(synonyms)
