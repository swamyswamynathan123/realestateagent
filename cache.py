"""
cache.py — Persistent LLM response cache backed by stdlib sqlite3.

Implements langchain_core.caches.BaseCache so it integrates with LangChain's
global cache registry — no extra packages needed beyond what's already required.

How it works
------------
LangChain intercepts every llm.invoke() call.  Before hitting the API it calls
cache.lookup(prompt, llm_string).  On a hit it returns the stored Generation
objects.  On a miss it calls the API and then calls cache.update() to store the
result.  All of this happens inside ChatOpenAI — our tool code is unaffected.

Cache key
---------
SHA-256 of (prompt + NULL-separator + llm_string).  The llm_string encodes the
model name, temperature, max_tokens, and other call parameters so a settings
change correctly produces a new key.

Persistence
-----------
Stored in a local SQLite file (default: .langchain_cache.db).  The file is
created automatically; re-runs of the same address skip the API entirely.
Add the file to .gitignore so cached API responses aren't committed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from typing import Optional, Sequence

from langchain_core.caches import BaseCache
from langchain_core.outputs import ChatGeneration, Generation

logger = logging.getLogger(__name__)

# Type alias used by BaseCache
RETURN_VAL_TYPE = Sequence[Generation]


class SQLiteCache(BaseCache):
    """
    Persistent LLM cache using stdlib sqlite3.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Created automatically if absent.
    """

    def __init__(self, db_path: str = ".langchain_cache.db") -> None:
        self._db_path = db_path
        self._init_db()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    value     TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ── Key derivation ────────────────────────────────────────────────────────

    @staticmethod
    def _make_key(prompt: str, llm_string: str) -> str:
        raw = f"{prompt}\x00{llm_string}"
        return hashlib.sha256(raw.encode()).hexdigest()

    # ── BaseCache interface ───────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with WAL mode for better Windows concurrency."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def lookup(self, prompt: str, llm_string: str) -> Optional[RETURN_VAL_TYPE]:
        """Return cached generations or None on a miss."""
        key = self._make_key(prompt, llm_string)
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT value FROM llm_cache WHERE cache_key = ?", (key,)
                ).fetchone()
            finally:
                conn.close()
            if row is None:
                return None
            items = json.loads(row[0])
            generations: list[Generation] = []
            for item in items:
                if item.get("type") == "ChatGeneration":
                    generations.append(ChatGeneration(**item))
                else:
                    generations.append(
                        Generation(**{k: v for k, v in item.items() if k != "type"})
                    )
            logger.debug("Cache HIT  key=%.12s…", key)
            return generations
        except Exception:
            logger.exception("Cache lookup error — treating as miss")
            return None

    def update(
        self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE
    ) -> None:
        """Persist the LLM response so future identical calls skip the API."""
        key = self._make_key(prompt, llm_string)
        try:
            serialized = json.dumps([g.model_dump() for g in return_val])
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO llm_cache (cache_key, value) VALUES (?, ?)",
                    (key, serialized),
                )
                conn.commit()
            finally:
                conn.close()
            logger.debug("Cache STORE key=%.12s…", key)
        except Exception:
            logger.exception("Cache update error — response not cached")

    def clear(self, **kwargs) -> None:
        """Delete all cached entries."""
        conn = self._connect()
        try:
            conn.execute("DELETE FROM llm_cache")
            conn.commit()
        finally:
            conn.close()
        logger.info("LLM cache cleared")

    # ── Convenience ───────────────────────────────────────────────────────────

    def size(self) -> int:
        """Return the number of cached entries."""
        try:
            conn = self._connect()
            try:
                return conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
            finally:
                conn.close()
        except Exception:
            return 0
