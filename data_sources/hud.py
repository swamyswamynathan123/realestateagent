"""
data_sources/hud.py — HUD Fair Market Rents (FMR)

Returns the official government-published monthly rent benchmarks
for 0–4 bedroom units, keyed by ZIP code.

Free API token: https://www.huduser.gov/hudapi/public/register.php
"""
from __future__ import annotations
import logging
import os
import re
from typing import Optional

import requests

from data_sources._cache import get as cache_get, put as cache_put

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.huduser.gov/hudapi/public/fmr/data"
_TIMEOUT  = 8


def _extract_zip(address: str) -> Optional[str]:
    m = re.search(r"\b(\d{5})\b", address)
    return m.group(1) if m else None


def get_fair_market_rents(address: str, api_key: Optional[str] = None) -> Optional[dict]:
    """Fetch HUD Fair Market Rents for the ZIP code in *address*.

    Returns a dict with fmr_studio, fmr_1br … fmr_4br (monthly dollars),
    county, metro_area, year, and source.  Returns None on failure.
    """
    zip_code = _extract_zip(address)
    if not zip_code:
        return None

    token = api_key or os.environ.get("HUD_API_KEY", "")
    if not token:
        return None

    cache_key = f"hud:fmr:{zip_code}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        r = requests.get(
            f"{_BASE_URL}/{zip_code}",
            params={"year": "2024"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()

        data = r.json()
        basic = data.get("data", {}).get("basicdata", {})
        if not basic:
            # Some ZIP codes resolve to a county-level entity ID;
            # the API returns smallareas = [] but basicdata may still exist.
            return None

        def _money(v) -> Optional[int]:
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        result: dict = {
            "zip":         zip_code,
            "county":      basic.get("countyname", ""),
            "metro_area":  basic.get("metroareaname", ""),
            "fmr_studio":  _money(basic.get("fmr_0")),
            "fmr_1br":     _money(basic.get("fmr_1")),
            "fmr_2br":     _money(basic.get("fmr_2")),
            "fmr_3br":     _money(basic.get("fmr_3")),
            "fmr_4br":     _money(basic.get("fmr_4")),
            "year":        basic.get("year", "2024"),
            "source":      "HUD FY2024 Fair Market Rents",
        }
        cache_put(cache_key, result, ttl_hours=720)  # FMR published annually
        return result

    except Exception:
        logger.warning("HUD FMR fetch failed for ZIP %s", zip_code, exc_info=True)
    return None
