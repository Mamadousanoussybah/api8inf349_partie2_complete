import os
from peewee import PostgresqlDatabase


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


db = PostgresqlDatabase(
    _env('DB_NAME', 'api8inf349'),
    user=_env('DB_USER', 'user'),
    password=_env('DB_PASSWORD', 'pass'),
    host=_env('DB_HOST', 'localhost'),
    port=int(_env('DB_PORT', '5432')),
)
