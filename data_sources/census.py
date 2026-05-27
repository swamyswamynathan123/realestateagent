"""
data_sources/census.py — US Census Bureau ACS 5-Year Estimates

Variables fetched per ZIP code:
  B25077_001E  Median value of owner-occupied housing units
  B19013_001E  Median household income (inflation-adjusted dollars)
  B01003_001E  Total population
  B25003_002E  Owner-occupied housing units
  B25003_003E  Renter-occupied housing units

Free API key (optional, raises rate limit):
  https://api.census.gov/data/key_signup.html

The API also works without a key at a lower rate limit (500 req/day),
so we do not require a key — pass one for production usage.
"""
from __future__ import annotations
import logging
import os
import re
from typing import Optional

import requests

from data_sources._cache import get as cache_get, put as cache_put

logger = logging.getLogger(__name__)

_BASE_URL  = "https://api.census.gov/data/2022/acs/acs5"
_VARIABLES = "B25077_001E,B19013_001E,B01003_001E,B25003_002E,B25003_003E"
_TIMEOUT   = 8


def _extract_zip(address: str) -> Optional[str]:
    """Pull a 5-digit ZIP code from an address string."""
    m = re.search(r"\b(\d{5})\b", address)
    return m.group(1) if m else None


def get_acs_data(address: str, api_key: Optional[str] = None) -> Optional[dict]:
    """Fetch ACS 5-year estimates for the ZIP code embedded in *address*.

    Returns a dict or None if the ZIP cannot be extracted or the request fails.
    """
    zip_code = _extract_zip(address)
    if not zip_code:
        return None

    cache_key = f"census:acs5:{zip_code}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    key = api_key or os.environ.get("CENSUS_API_KEY", "")
    params: dict = {
        "get": _VARIABLES,
        "for": f"zip code tabulation area:{zip_code}",
    }
    if key:
        params["key"] = key

    try:
        r = requests.get(_BASE_URL, params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        rows = r.json()
        if len(rows) < 2:
            return None

        headers = rows[0]
        values  = rows[1]
        raw     = dict(zip(headers, values))

        def _int(field: str) -> Optional[int]:
            try:
                v = int(raw.get(field, -1))
                return v if v >= 0 else None
            except (TypeError, ValueError):
                return None

        result: dict = {
            "zip":               zip_code,
            "median_home_value": _int("B25077_001E"),
            "median_income":     _int("B19013_001E"),
            "population":        _int("B01003_001E"),
            "owner_occupied":    _int("B25003_002E"),
            "renter_occupied":   _int("B25003_003E"),
            "source":            "US Census Bureau ACS 5-Year Estimates (2022)",
        }
        cache_put(cache_key, result, ttl_hours=168)  # Census data is stable; weekly refresh
        return result

    except Exception:
        logger.warning("Census ACS fetch failed for ZIP %s", zip_code, exc_info=True)
    return None
