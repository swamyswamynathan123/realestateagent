"""
data_sources/fred.py — FRED API (Federal Reserve Bank of St. Louis)

Fetches current 30-year and 15-year fixed mortgage rates from the
Freddie Mac Primary Mortgage Market Survey via FRED.

Free API key: https://fred.stlouisfed.org/docs/api/api_key.html
"""
from __future__ import annotations
import logging
import os
from datetime import datetime
from typing import Optional

import requests

from data_sources._cache import get as cache_get, put as cache_put

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
_TIMEOUT  = 8


def _latest_value(series_id: str, api_key: str) -> Optional[float]:
    """Return the most-recent non-null observation for a FRED series."""
    cache_key = f"fred:{series_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return float(cached)

    try:
        r = requests.get(
            _BASE_URL,
            params={
                "series_id":        series_id,
                "sort_order":       "desc",
                "limit":            "5",          # a few in case latest is "."
                "api_key":          api_key,
                "file_type":        "json",
                "observation_start": "2020-01-01",
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        obs = [o for o in r.json().get("observations", []) if o["value"] != "."]
        if obs:
            val = float(obs[0]["value"])
            cache_put(cache_key, val, ttl_hours=8)  # Freddie Mac surveys weekly
            return val
    except Exception:
        logger.warning("FRED fetch failed for series %s", series_id, exc_info=True)
    return None


def get_mortgage_rates(api_key: Optional[str] = None) -> Optional[dict]:
    """Return current 30-yr and 15-yr fixed mortgage rates.

    Returns a dict with keys: rate_30yr, rate_15yr, as_of, source.
    Returns None if no API key is configured or the request fails.
    """
    key = api_key or os.environ.get("FRED_API_KEY", "")
    if not key:
        return None

    rate_30 = _latest_value("MORTGAGE30US", key)
    rate_15 = _latest_value("MORTGAGE15US", key)

    if rate_30 is None:
        return None

    return {
        "rate_30yr": rate_30,
        "rate_15yr": rate_15,
        "as_of":     datetime.now().strftime("%B %Y"),
        "source":    "Freddie Mac Primary Mortgage Market Survey via FRED",
    }
