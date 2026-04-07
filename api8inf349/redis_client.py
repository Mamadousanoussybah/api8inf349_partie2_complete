import json
import os

import redis


def get_redis_url():
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


# Connexion pour le cache JSON de l'application
def get_cache_redis_connection():
    return redis.from_url(get_redis_url(), decode_responses=True)


# Connexion pour RQ / jobs binaires
def get_queue_redis_connection():
    return redis.from_url(get_redis_url(), decode_responses=False)


def get_redis_connection():
    # Gardé pour compatibilité avec le reste du code applicatif
    return get_cache_redis_connection()


def get_queue_name():
    return "default"


def get_queue():
    from rq import Queue
    return Queue(get_queue_name(), connection=get_queue_redis_connection())


def cache_order_key(order_id: int) -> str:
    return f"order:{order_id}"


def processing_order_key(order_id: int) -> str:
    return f"order:{order_id}:processing"


def save_cached_order(order_id: int, payload: dict):
    conn = get_cache_redis_connection()
    conn.set(cache_order_key(order_id), json.dumps(payload))


def load_cached_order(order_id: int):
    conn = get_cache_redis_connection()
    data = conn.get(cache_order_key(order_id))
    if not data:
        return None
    return json.loads(data)


def set_processing(order_id: int, value: bool):
    conn = get_cache_redis_connection()
    key = processing_order_key(order_id)
    if value:
        conn.set(key, "1")
    else:
        conn.delete(key)


def is_processing(order_id: int) -> bool:
    conn = get_cache_redis_connection()
    return conn.exists(processing_order_key(order_id)) == 1