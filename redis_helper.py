import json
import os
import pickle
from pathlib import Path

import redis

conn_pool = redis.ConnectionPool(
    host=os.getenv('REDIS_HOST'),
    username=os.getenv('REDIS_USERNAME'),
    password=os.getenv('REDIS_PASSWORD'),
    port=os.getenv('REDIS_PORT'),
    connection_class=redis.SSLConnection
)

ROOT_PATH = Path("data/")


def write_to_disk(key: str, value):
    with open(str(ROOT_PATH / key), "wb+") as f:
        pickle.dump(value, f)


def read_from_disk(key: str):
    try:
        with open(str(ROOT_PATH / key), "rb+") as f:
            return pickle.load(f)
    except:
        return None


def write_to_redis(key: str, value):
    with redis.StrictRedis(connection_pool=conn_pool) as conn:
        pickled_val = pickle.dumps(value)
        return conn.set(key, pickled_val)


def load_from_redis(key: str):
    with redis.StrictRedis(connection_pool=conn_pool) as conn:
        val = conn.get(key)
        if val:
            return pickle.loads(val)
