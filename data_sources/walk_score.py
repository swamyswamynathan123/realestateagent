"""
data_sources/walk_score.py — Walk Score API

Returns Walk Score, Transit Score, and Bike Score for an address.
Requires (lat, lon) from geocoding for best accuracy.

Free API key (5,000 req/day): https://www.walkscore.com/professional/api.php
"""
from __future__ import annotations
import logging
import os
from typing import Optional

import requests

from data_sources._cache import get as cache_get, put as cache_put

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.walkscore.com/score"
_TIMEOUT  = 8


def get_walk_score(
    address: str,
    lat: float,
    lon: float,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Fetch Walk Score, Transit Score, and Bike Score.

    Parameters
    ----------
    address:  Full property address (used as the Walk Score query).
    lat, lon: Coordinates from geocoding (improve accuracy).
    api_key:  Walk Score API key; falls back to WALKSCORE_API_KEY env var.

    Returns a dict or None if no key / request fails.
    """
    key = api_key or os.environ.get("WALKSCORE_API_KEY", "")
    if not key:
        return None

    # Cache keyed by address (lat/lon resolve to same place)
    cache_key = f"walkscore:{address.lower().strip()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        r = requests.get(
            _BASE_URL,
            params={
                "format":   "json",
                "address":  address,
                "lat":      lat,
                "lon":      lon,
                "transit":  1,
                "bike":     1,
                "wsapikey": key,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        d = r.json()

        # Walk Score API returns status 1 (ok) or 2 (score is being calculated)
        status = d.get("status")
        if status not in (1, 2):
            logger.warning("Walk Score API returned status %s for %s", status, address)
            return None

        transit = d.get("transit") or {}
        bike    = d.get("bike")    or {}

        result: dict = {
            "walk_score":    d.get("walkscore"),
            "walk_desc":     d.get("description", ""),
            "transit_score": transit.get("score"),
            "transit_desc":  transit.get("description", ""),
            "bike_score":    bike.get("score"),
            "bike_desc":     bike.get("description", ""),
            "source":        "Walk Score® (www.walkscore.com)",
        }
        cache_put(cache_key, result, ttl_hours=720)  # Walk scores rarely change
        return result

    except Exception:
        logger.warning("Walk Score fetch failed for %s", address, exc_info=True)
    return None
