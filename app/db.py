"""Postgres connection pool."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from psycopg_pool import ConnectionPool

_POOL: ConnectionPool | None = None


def _dsn() -> str:
    return (
        f"host={os.getenv('DECIPHER_DB_HOST', '127.0.0.1')} "
        f"port={os.getenv('DECIPHER_DB_PORT', '55432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'decipher')} "
        f"user={os.getenv('POSTGRES_USER', 'decipher')} "
        f"password={os.getenv('POSTGRES_PASSWORD', 'decipher_local_dev')}"
    )


def pool() -> ConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = ConnectionPool(_dsn(), min_size=1, max_size=8, kwargs={"autocommit": True})
    return _POOL


@contextmanager
def conn() -> Iterator:
    with pool().connection() as c:
        yield c


def rows(sql: str, params: tuple = ()) -> list[dict]:
    with conn() as c, c.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def scalar(sql: str, params: tuple = ()):
    with conn() as c, c.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return row[0] if row else None


def event(action: str, *, severity: str = "info", actor: str | None = None,
          subject_id: str | None = None, payload: dict | None = None) -> None:
    """Write to events_log. Every state transition / agent run / API call goes here."""
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
                 VALUES (%s, %s, %s, %s, %s::jsonb)""",
            (actor, action, severity, subject_id,
             None if payload is None else __import__("json").dumps(payload)),
        )
