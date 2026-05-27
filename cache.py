"""
cache.py — Persistent cache backed by stdlib sqlite3.

Two independent tables share one database file:

  llm_cache    — LangChain LLM response cache (implements BaseCache).
                 Key: SHA-256(prompt + llm_string).
                 No TTL — LLM responses are deterministic given the same input.

  search_cache — Tavily web-search result cache.
                 Key: SHA-256(query + sorted-domain-list).
                 TTL: configurable (default 24 h) so stale property data expires.

How it works
------------
LangChain intercepts every llm.invoke() call.  Before hitting the OpenAI API it
calls cache.lookup(prompt, llm_string).  On a hit it returns stored Generation
objects; on a miss it calls the API and then calls cache.update() to store the
result.  Our tool code is unaffected.

For web searches, _web_search() in BaseRealEstateTool calls lookup_search()
before hitting Tavily.  A hit returns the cached text instantly (no HTTP call);
a miss calls Tavily and then calls store_search() so the next run is free.

Because the Tavily result is now stable between runs, the LLM prompt is also
stable, so the LLM cache can hit on the second run too.

Persistence
-----------
Both tables live in .langchain_cache.db (WAL mode for Windows concurrency).
Add that file to .gitignore — it contains API response data, not source code.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from typing import Optional, Sequence

from langchain_core.caches import BaseCache
from langchain_core.outputs import ChatGeneration, Generation

logger = logging.getLogger(__name__)

# Type alias used by BaseCache
RETURN_VAL_TYPE = Sequence[Generation]

# Default TTL for web-search results (24 hours).
# Real estate data changes daily; shorter TTL = fresher data, more Tavily calls.
SEARCH_CACHE_TTL_SECS: int = 60 * 60 * 24


class SQLiteCache(BaseCache):
    """
    Persistent LLM + web-search cache using stdlib sqlite3.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Created automatically if absent.
    search_ttl_secs:
        How long web-search results are considered fresh (default: 86 400 = 24 h).
        Pass 0 to disable search-result expiry.
    """

    def __init__(
        self,
        db_path: str = ".langchain_cache.db",
        search_ttl_secs: int = SEARCH_CACHE_TTL_SECS,
    ) -> None:
        self._db_path = db_path
        self._search_ttl = search_ttl_secs
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    results   TEXT NOT NULL,
                    cached_at INTEGER NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Open a WAL-mode connection (better concurrency on Windows)."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @staticmethod
    def _make_key(a: str, b: str) -> str:
        """SHA-256 of two strings joined by a NULL separator."""
        return hashlib.sha256(f"{a}\x00{b}".encode()).hexdigest()

    # ── LLM cache (BaseCache interface) ───────────────────────────────────────

    def lookup(self, prompt: str, llm_string: str) -> Optional[RETURN_VAL_TYPE]:
        """Return cached LLM generations or None on a miss."""
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
            logger.debug("LLM cache HIT   key=%.12s…", key)
            return generations
        except Exception:
            logger.exception("LLM cache lookup error — treating as miss")
            return None

    def update(
        self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE
    ) -> None:
        """Persist an LLM response so future identical calls skip the API."""
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
            logger.debug("LLM cache STORE key=%.12s…", key)
        except Exception:
            logger.exception("LLM cache update error — response not cached")

    def clear(self, **kwargs) -> None:
        """Delete all LLM *and* search cache entries."""
        conn = self._connect()
        try:
            conn.execute("DELETE FROM llm_cache")
            conn.execute("DELETE FROM search_cache")
            conn.commit()
        finally:
            conn.close()
        logger.info("Cache cleared (both tables)")

    # ── Web-search cache ──────────────────────────────────────────────────────

    @staticmethod
    def _search_key(query: str, domains: list[str] | None) -> str:
        domain_str = ",".join(sorted(domains)) if domains else ""
        return hashlib.sha256(f"{query}\x00{domain_str}".encode()).hexdigest()

    def lookup_search(
        self,
        query: str,
        domains: list[str] | None = None,
    ) -> Optional[str]:
        """Return cached search text, or None on a miss / expired entry."""
        key = self._search_key(query, domains)
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT results, cached_at FROM search_cache WHERE cache_key = ?",
                    (key,),
                ).fetchone()
            finally:
                conn.close()
            if row is None:
                return None
            results_text, cached_at = row
            if self._search_ttl > 0 and (time.time() - cached_at) > self._search_ttl:
                logger.debug("Search cache EXPIRED key=%.12s…", key)
                return None  # treat as miss; will be refreshed on next store
            logger.debug("Search cache HIT   key=%.12s…", key)
            return results_text
        except Exception:
            logger.exception("Search cache lookup error — treating as miss")
            return None

    def store_search(
        self,
        query: str,
        results: str,
        domains: list[str] | None = None,
    ) -> None:
        """Persist web-search results for this query + domain combination."""
        key = self._search_key(query, domains)
        try:
            conn = self._connect()
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO search_cache
                       (cache_key, results, cached_at) VALUES (?, ?, ?)""",
                    (key, results, int(time.time())),
                )
                conn.commit()
            finally:
                conn.close()
            logger.debug("Search cache STORE key=%.12s…", key)
        except Exception:
            logger.exception("Search cache store error — result not cached")

    # ── Size helpers ──────────────────────────────────────────────────────────

    def size(self) -> int:
        """Number of cached LLM responses."""
        return self._table_count("llm_cache")

    def search_size(self) -> int:
        """Number of cached web-search results."""
        return self._table_count("search_cache")

    def _table_count(self, table: str) -> int:
        try:
            conn = self._connect()
            try:
                return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
            finally:
                conn.close()
        except Exception:
            return 0
