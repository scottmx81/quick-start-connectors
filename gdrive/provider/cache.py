from abc import abstractmethod

import redis
from cachetools import TTLCache
from flask import current_app as app


CACHE_TYPE_NONE = "none"
CACHE_TYPE_MEMORY = "memory"
CACHE_TYPE_REDIS = "redis"

CACHE_EXPIRE_TIME = 60 * 5


backend = None


class CacheBackend:
    def get_cache_key(self, document_id: str) -> str:
        return f"document_text_{document_id}"

    @abstractmethod
    def cache_document_text(self, document_id, text):
        pass

    @abstractmethod
    def get_document_text(self, document_id: str) -> str:
        pass


class MemoryBackend(CacheBackend):
    maxsize = 1000

    def __init__(self):
        self.ttl_cache = TTLCache(self.maxsize, CACHE_EXPIRE_TIME)

    def cache_document_text(self, document_id: str, text: str) -> None:
        cache_key = self.get_cache_key(document_id)
        self.ttl_cache[cache_key] = text

    def get_document_text(self, document_id: str):
        cache_key = self.get_cache_key(document_id)
        return self.ttl_cache.get(cache_key)


class RedisBackend(CacheBackend):
    def __init__(self):
        self.r = redis.Redis(host="localhost", port=6379, db=0, protocol=3)

    def cache_document_text(self, document_id: str, text: str) -> None:
        cache_key = self.get_cache_key(document_id)
        self.r.set(cache_key, text, CACHE_EXPIRE_TIME)

    def get_document_text(self, document_id: str) -> str:
        cache_key = self.get_cache_key(document_id)
        document_text = self.r.get(cache_key)
        return document_text.decode() if document_text else None


CACHE_BACKENDS = {
    CACHE_TYPE_MEMORY: MemoryBackend,
    CACHE_TYPE_REDIS: RedisBackend,
}


def init(type):
    global backend

    if not type:
        return

    assert type in CACHE_BACKENDS, "Invalid cache backend"
    backend = CACHE_BACKENDS[type]()


def get_document_text(document_id) -> str:
    assert backend, "Caching not configured"
    return backend.get_document_text(document_id)


def cache_document_text(document_id: str, value: str):
    assert backend, "Caching not configured"
    backend.cache_document_text(document_id, value)