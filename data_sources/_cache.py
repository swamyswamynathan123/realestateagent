"""
data_sources/_cache.py — Lightweight SQLite TTL cache for external API calls.

Separate from the LLM cache so data-source responses can have their own
retention policy (typically hours to days, not forever).
"""
from __future__ import annotations
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional  # noqa: F401

logger = logging.getLogger(__name__)

_CACHE_DB = ".datasources_cache.db"
_INIT_DONE: set[str] = set()   # avoid re-running CREATE TABLE every call


def _init(db: str) -> None:
    if db in _INIT_DONE:
        return
    try:
        with sqlite3.connect(db) as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("""
                CREATE TABLE IF NOT EXISTS ds_cache (
                    key     TEXT PRIMARY KEY,
                    value   TEXT NOT NULL,
                    expires TEXT NOT NULL
                )
            """)
            con.commit()
        _INIT_DONE.add(db)
    except Exception:
        logger.debug("DS cache init failed for %s", db, exc_info=True)


def get(key: str, db: Optional[str] = None) -> Optional[Any]:
    """Return the cached value, or None if absent / expired.

    *db* defaults to ``_CACHE_DB`` resolved at call time (not import time)
    so that test fixtures can monkeypatch the module variable.
    """
    _db = db if db is not None else _CACHE_DB
    try:
        _init(_db)
        with sqlite3.connect(_db) as con:
            row = con.execute(
                "SELECT value, expires FROM ds_cache WHERE key=?", (key,)
            ).fetchone()
        if row:
            if datetime.now() < datetime.fromisoformat(row[1]):
                return json.loads(row[0])
            # Expired — lazy delete
            with sqlite3.connect(_db) as con:
                con.execute("DELETE FROM ds_cache WHERE key=?", (key,))
                con.commit()
    except Exception:
        logger.debug("DS cache get failed: %s", key, exc_info=True)
    return None


def put(key: str, value: Any, ttl_hours: float = 24, db: Optional[str] = None) -> None:
    """Store *value* under *key* with the given TTL.

    *db* defaults to ``_CACHE_DB`` resolved at call time.
    """
    _db = db if db is not None else _CACHE_DB
    try:
        _init(_db)
        expires = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
        with sqlite3.connect(_db) as con:
            con.execute(
                "INSERT OR REPLACE INTO ds_cache (key, value, expires) VALUES (?,?,?)",
                (key, json.dumps(value), expires),
            )
            con.commit()
    except Exception:
        logger.debug("DS cache put failed: %s", key, exc_info=True)
