"""
data_sources/fema.py — FEMA National Flood Hazard Layer (NFHL)

Determines the flood zone for a pair of coordinates using FEMA's
public ArcGIS REST service.  No API key required.

Service: https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer
Layer 28: Flood Hazard Zones (combined)
"""
from __future__ import annotations
import logging
from typing import Optional

import requests

from data_sources._cache import get as cache_get, put as cache_put

logger = logging.getLogger(__name__)

_URL     = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
_TIMEOUT = 10


# Human-readable descriptions for FLD_ZONE codes
_ZONE_INFO: dict[str, tuple[str, str]] = {
    # (risk_level, description)
    "A":   ("High",          "Special Flood Hazard Area — 1% annual chance flood"),
    "AE":  ("High",          "Special Flood Hazard Area — Base Flood Elevation determined"),
    "AH":  ("High",          "Special Flood Hazard Area — Shallow ponding"),
    "AO":  ("High",          "Special Flood Hazard Area — Shallow river/stream overflow"),
    "AR":  ("High",          "Special Flood Hazard Area — Area protected by flood control system under construction"),
    "A99": ("High",          "Special Flood Hazard Area — Protected by levee under construction"),
    "V":   ("High Coastal",  "Coastal Special Flood Hazard Area — Velocity wave action"),
    "VE":  ("High Coastal",  "Coastal Special Flood Hazard Area — Velocity wave action, BFE determined"),
    "X":   ("Low/Moderate",  "Outside Special Flood Hazard Area — Minimal flood hazard"),
    "B":   ("Low/Moderate",  "Moderate flood hazard (older FIRM designation)"),
    "C":   ("Minimal",       "Minimal flood hazard (older FIRM designation)"),
    "D":   ("Undetermined",  "Possible flood hazard — not studied"),
}

_SFHA_ZONES = frozenset({"A", "AE", "AH", "AO", "AR", "A99", "V", "VE"})


def _describe(zone: str) -> tuple[str, str, bool]:
    """Return (risk_level, description, is_sfha) for a zone code."""
    zone = zone.strip().upper()
    if zone in _ZONE_INFO:
        risk, desc = _ZONE_INFO[zone]
        return risk, desc, zone in _SFHA_ZONES
    if zone.startswith("A"):
        return "High", "Special Flood Hazard Area", True
    if zone.startswith("V"):
        return "High Coastal", "Coastal Special Flood Hazard Area — Velocity wave action", True
    if zone in ("X", "B", "C"):
        return "Low/Moderate", "Outside or minimal flood hazard area", False
    return "Unknown", f"Zone {zone} — consult FEMA FIRM panel", False


def get_flood_zone(lat: float, lon: float) -> Optional[dict]:
    """Return flood zone info for the given coordinates.

    Returns a dict with keys: zone, zone_subtype, sfha, risk_level,
    description, base_flood_elevation, source.
    Returns None if the location is outside FEMA coverage or the
    request fails.
    """
    # Round to 4 decimal places (~11 m) for cache key stability
    cache_key = f"fema:nfhl:{lat:.4f},{lon:.4f}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        r = requests.get(
            _URL,
            params={
                "geometry":       f"{lon},{lat}",
                "geometryType":   "esriGeometryPoint",
                "inSR":           "4326",
                "spatialRel":     "esriSpatialRelIntersects",
                "outFields":      "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE",
                "returnGeometry": "false",
                "f":              "json",
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data  = r.json()

        # FEMA returns an error dict when the service is unavailable
        if "error" in data:
            logger.warning("FEMA NFHL error: %s", data["error"])
            return None

        features = data.get("features", [])
        if not features:
            return None   # No flood zone data for this location

        attrs = features[0].get("attributes", {})
        zone  = (attrs.get("FLD_ZONE") or "").strip().upper()
        if not zone:
            return None

        risk, desc, sfha = _describe(zone)

        result: dict = {
            "zone":                zone,
            "zone_subtype":        (attrs.get("ZONE_SUBTY") or "").strip(),
            "sfha":                sfha,
            "risk_level":          risk,
            "description":         desc,
            "base_flood_elevation": attrs.get("STATIC_BFE"),
            "source":              "FEMA National Flood Hazard Layer (NFHL)",
        }
        cache_put(cache_key, result, ttl_hours=720)  # FIRMs updated infrequently
        return result

    except Exception:
        logger.warning(
            "FEMA NFHL fetch failed for %.4f, %.4f", lat, lon, exc_info=True
        )
    return None
