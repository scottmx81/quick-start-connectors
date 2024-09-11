import redis
from cachetools import TTLCache
from flask import current_app as app


CACHE_TYPE_NONE = "none"
CACHE_TYPE_MEMORY = "memory"
CACHE_TYPE_REDIS = "redis"

CACHE_EXPIRE_TIME = 60 * 5
CACHE_MEMORY_MAXSIZE = 1000

cache_type = CACHE_TYPE_NONE
memory_cache = None
r = None


def init(type):
    global cache_type
    global memory_cache
    global r

    if type:
        cache_type = type
    else:
        cache_type = CACHE_TYPE_NONE

    if type == CACHE_TYPE_MEMORY:
        memory_cache = TTLCache(CACHE_MEMORY_MAXSIZE, CACHE_EXPIRE_TIME)

    if type == CACHE_TYPE_REDIS:
        r = redis.Redis(host="localhost", port=6379, db=0, protocol=3)


def get(key) -> str:
    value = None

    if cache_type == CACHE_TYPE_MEMORY:
        value = memory_cache.get(key)
    elif cache_type == CACHE_TYPE_REDIS:
        value = r.get(key).decode()

    return value


def set(key, value):
    if cache_type == CACHE_TYPE_MEMORY:
        memory_cache[key] = value
    if cache_type == CACHE_TYPE_REDIS:
        r.set(key, value, CACHE_EXPIRE_TIME)
