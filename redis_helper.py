import os
import pickle
import redis


def write_to_redis(key: str, value):
    conn_pool = redis.ConnectionPool(
        host=os.getenv('REDIS_HOST'), username=os.getenv('REDIS_USERNAME'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), connection_class=redis.SSLConnection
    )
    with redis.StrictRedis(connection_pool=conn_pool) as conn:
        pickled_val = pickle.dumps(value)
        return conn.set(key, pickled_val)


def load_from_redis(key: str):
    conn_pool = redis.ConnectionPool(
        host=os.getenv('REDIS_HOST'), username=os.getenv('REDIS_USERNAME'), password=os.getenv('REDIS_PASSWORD'),
        port=os.getenv('REDIS_PORT'), connection_class=redis.SSLConnection
    )
    with redis.StrictRedis(connection_pool=conn_pool) as conn:
        val = conn.get(key)
        if val:
            return pickle.loads(val)
