"""
tests/test_data_sources.py — Unit tests for data_sources/ modules.

All tests are fully mocked (no live API calls).
"""
import pytest
from unittest.mock import MagicMock, patch
import json


# ── Cache helper ───────────────────────────────────────────────────────────────

@pytest.fixture
def clean_ds_cache(tmp_path, monkeypatch):
    """Redirect the DS cache DB to a temp file so tests stay isolated."""
    db_path = str(tmp_path / "test_ds_cache.db")
    monkeypatch.setattr("data_sources._cache._CACHE_DB", db_path)
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())
    return db_path


# ── _cache tests ───────────────────────────────────────────────────────────────

def test_cache_put_and_get(tmp_path):
    db = str(tmp_path / "cache_test.db")
    from data_sources._cache import get, put
    put("key1", {"value": 42}, ttl_hours=1, db=db)
    assert get("key1", db=db) == {"value": 42}


def test_cache_miss_returns_none(tmp_path):
    db = str(tmp_path / "cache_test2.db")
    from data_sources._cache import get
    assert get("nonexistent", db=db) is None


def test_cache_expired_returns_none(tmp_path):
    from datetime import datetime, timedelta
    import sqlite3
    db = str(tmp_path / "cache_test3.db")
    from data_sources._cache import put, get
    put("key_exp", "stale", ttl_hours=1, db=db)
    # Manually expire it
    past = (datetime.now() - timedelta(hours=2)).isoformat()
    with sqlite3.connect(db) as con:
        con.execute("UPDATE ds_cache SET expires=? WHERE key=?", (past, "key_exp"))
        con.commit()
    assert get("key_exp", db=db) is None


# ── FRED tests ─────────────────────────────────────────────────────────────────

def test_fred_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    from data_sources.fred import get_mortgage_rates
    assert get_mortgage_rates(api_key=None) is None


def test_fred_returns_rates(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mock_30 = {"observations": [{"value": "6.87"}, {"value": "6.90"}]}
    mock_15 = {"observations": [{"value": "6.21"}]}

    def fake_get(url, params=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        if "MORTGAGE30US" in (params or {}).get("series_id", ""):
            m.json.return_value = mock_30
        else:
            m.json.return_value = mock_15
        return m

    with patch("data_sources.fred.requests.get", side_effect=fake_get):
        from data_sources.fred import get_mortgage_rates
        rates = get_mortgage_rates(api_key="fake-key")

    assert rates is not None
    assert rates["rate_30yr"] == pytest.approx(6.87)
    assert rates["rate_15yr"] == pytest.approx(6.21)
    assert "Freddie Mac" in rates["source"]


def test_fred_returns_none_on_http_error(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "fred_err.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    def bad_get(*a, **kw):
        raise Exception("connection refused")

    with patch("data_sources.fred.requests.get", side_effect=bad_get):
        from data_sources.fred import get_mortgage_rates
        assert get_mortgage_rates(api_key="fake-key") is None


# ── Census tests ───────────────────────────────────────────────────────────────

def test_census_returns_none_without_zip():
    from data_sources.census import get_acs_data
    # Address with no ZIP code
    result = get_acs_data("123 Main St, Austin, TX")
    assert result is None


def test_census_returns_data_for_zip(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mock_response = [
        ["B25077_001E", "B19013_001E", "B01003_001E", "B25003_002E", "B25003_003E", "zip code tabulation area"],
        ["450000",      "85000",       "32000",        "8000",         "5000",         "78701"],
    ]

    def fake_get(url, params=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = mock_response
        return m

    with patch("data_sources.census.requests.get", side_effect=fake_get):
        from data_sources.census import get_acs_data
        result = get_acs_data("123 Main St, Austin, TX 78701")

    assert result is not None
    assert result["zip"] == "78701"
    assert result["median_home_value"] == 450_000
    assert result["median_income"] == 85_000
    assert result["population"] == 32_000
    assert result["owner_occupied"] == 8_000
    assert result["renter_occupied"] == 5_000


def test_census_handles_api_error(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "census_err.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    with patch("data_sources.census.requests.get", side_effect=Exception("timeout")):
        from data_sources.census import get_acs_data
        assert get_acs_data("123 Main St, Austin, TX 78701") is None


def test_census_handles_non_json_response(monkeypatch, tmp_path):
    """Census API returns plain text for ZIPs that aren't ZCTAs (e.g. 93001)."""
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "census_nonjson.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = "No results were returned by your request."

    with patch("data_sources.census.requests.get", return_value=mock_resp):
        from data_sources.census import get_acs_data
        # Must return None gracefully, not raise JSONDecodeError
        result = get_acs_data("123 Main St, Ventura, CA 93001")
        assert result is None


# ── HUD tests ──────────────────────────────────────────────────────────────────

def test_hud_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("HUD_API_KEY", raising=False)
    from data_sources.hud import get_fair_market_rents
    assert get_fair_market_rents("123 Main St, Austin, TX 78701") is None


def test_hud_returns_fmr(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mock_response = {
        "data": {
            "basicdata": {
                "year": "2024",
                "countyname": "Travis County",
                "metroareaname": "Austin-Round Rock, TX HUD Metro FMR Area",
                "fmr_0": 1350,
                "fmr_1": 1520,
                "fmr_2": 1890,
                "fmr_3": 2340,
                "fmr_4": 2680,
            }
        }
    }

    def fake_get(url, params=None, headers=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = mock_response
        return m

    with patch("data_sources.hud.requests.get", side_effect=fake_get):
        from data_sources.hud import get_fair_market_rents
        result = get_fair_market_rents("123 Main St, Austin, TX 78701", api_key="test-token")

    assert result is not None
    assert result["zip"] == "78701"
    assert result["fmr_2br"] == 1890
    assert result["county"] == "Travis County"
    assert "HUD" in result["source"]


def test_hud_returns_none_on_error(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "hud_err.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    with patch("data_sources.hud.requests.get", side_effect=Exception("401 Unauthorized")):
        from data_sources.hud import get_fair_market_rents
        assert get_fair_market_rents("123 Main St, Austin, TX 78701", api_key="bad-token") is None


# ── Walk Score tests ───────────────────────────────────────────────────────────

def test_walkscore_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("WALKSCORE_API_KEY", raising=False)
    from data_sources.walk_score import get_walk_score
    assert get_walk_score("123 Main St", 30.0, -97.0) is None


def test_walkscore_returns_scores(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mock_response = {
        "status":      1,
        "walkscore":   88,
        "description": "Walker's Paradise",
        "transit": {"score": 72, "description": "Excellent Transit"},
        "bike":    {"score": 65, "description": "Bikeable"},
    }

    def fake_get(url, params=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = mock_response
        return m

    with patch("data_sources.walk_score.requests.get", side_effect=fake_get):
        from data_sources.walk_score import get_walk_score
        result = get_walk_score("123 Main St, Austin, TX 78701", 30.2672, -97.7431, api_key="test-key")

    assert result is not None
    assert result["walk_score"] == 88
    assert result["transit_score"] == 72
    assert result["bike_score"] == 65
    assert "Walker's Paradise" in result["walk_desc"]


def test_walkscore_handles_bad_status(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    def fake_get(url, params=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = {"status": 40, "walkscore": None}   # error status
        return m

    with patch("data_sources.walk_score.requests.get", side_effect=fake_get):
        from data_sources.walk_score import get_walk_score
        assert get_walk_score("123 Main St", 30.0, -97.0, api_key="test-key") is None


# ── FEMA tests ─────────────────────────────────────────────────────────────────

def test_fema_returns_flood_zone(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mock_response = {
        "features": [
            {
                "attributes": {
                    "FLD_ZONE":  "AE",
                    "ZONE_SUBTY": "",
                    "SFHA_TF":  "T",
                    "STATIC_BFE": 425.0,
                }
            }
        ]
    }

    def fake_get(url, params=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = mock_response
        return m

    with patch("data_sources.fema.requests.get", side_effect=fake_get):
        from data_sources.fema import get_flood_zone
        result = get_flood_zone(30.2672, -97.7431)

    assert result is not None
    assert result["zone"] == "AE"
    assert result["sfha"] is True
    assert result["risk_level"] == "High"
    assert "Base Flood Elevation" in result["description"]
    assert result["base_flood_elevation"] == pytest.approx(425.0)


def test_fema_returns_low_risk_zone(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mock_response = {
        "features": [
            {"attributes": {"FLD_ZONE": "X", "ZONE_SUBTY": "", "SFHA_TF": "F", "STATIC_BFE": None}}
        ]
    }

    def fake_get(url, params=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = mock_response
        return m

    with patch("data_sources.fema.requests.get", side_effect=fake_get):
        from data_sources.fema import get_flood_zone
        result = get_flood_zone(47.6062, -122.3321)

    assert result is not None
    assert result["zone"] == "X"
    assert result["sfha"] is False
    assert result["risk_level"] == "Low/Moderate"


def test_fema_returns_none_when_no_features(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    def fake_get(url, params=None, timeout=None):
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.json.return_value = {"features": []}
        return m

    with patch("data_sources.fema.requests.get", side_effect=fake_get):
        from data_sources.fema import get_flood_zone
        assert get_flood_zone(0.0, 0.0) is None


def test_fema_returns_none_on_error(monkeypatch, tmp_path):
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    with patch("data_sources.fema.requests.get", side_effect=Exception("timeout")):
        from data_sources.fema import get_flood_zone
        assert get_flood_zone(30.0, -97.0) is None


# ── Tool integration: real data injected into prompt ──────────────────────────

def test_mortgage_tool_injects_fred_rates(mock_llm, monkeypatch, mocker, tmp_path):
    """MortgageTool should include real FRED rates in the LLM prompt when available."""
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    fake_rates = {"rate_30yr": 6.87, "rate_15yr": 6.21,
                  "as_of": "May 2025", "source": "Freddie Mac via FRED"}
    mocker.patch("data_sources.fred.get_mortgage_rates", return_value=fake_rates)
    mocker.patch("data_sources.census.get_acs_data", return_value=None)

    from tools.property_analysis import MortgageTool
    result = MortgageTool(llm=mock_llm).run("123 Main St, Austin, TX 78701", purchase_price=400000)

    assert result["status"] == "success"
    user_msg = mock_llm.invoke.call_args[0][0][-1].content
    assert "6.87" in user_msg
    assert "Freddie Mac" in user_msg


def test_rental_tool_injects_hud_fmr(mock_llm, monkeypatch, mocker, tmp_path):
    """RentalTool should include HUD FMR figures in the LLM prompt when available."""
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    fake_fmr = {
        "zip": "78701", "county": "Travis", "metro_area": "Austin Metro",
        "fmr_studio": 1350, "fmr_1br": 1520, "fmr_2br": 1890,
        "fmr_3br": 2340, "fmr_4br": 2680, "year": "2024",
        "source": "HUD FY2024 Fair Market Rents",
    }
    mocker.patch("data_sources.hud.get_fair_market_rents", return_value=fake_fmr)
    mocker.patch("data_sources.census.get_acs_data", return_value=None)

    from tools.property_analysis import RentalTool
    result = RentalTool(llm=mock_llm).run("123 Main St, Austin, TX 78701")

    assert result["status"] == "success"
    user_msg = mock_llm.invoke.call_args[0][0][-1].content
    assert "1,890" in user_msg   # 2BR FMR
    assert "HUD" in user_msg


def test_neighborhood_tool_injects_walkscore(mock_llm, monkeypatch, mocker, tmp_path):
    """NeighborhoodTool should include Walk Score in the LLM prompt when available."""
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mocker.patch("utils.geocode_address", return_value=(30.2672, -97.7431))
    mocker.patch("data_sources.walk_score.get_walk_score", return_value={
        "walk_score": 88, "walk_desc": "Walker's Paradise",
        "transit_score": 72, "transit_desc": "Excellent Transit",
        "bike_score": 65, "bike_desc": "Bikeable",
        "source": "Walk Score®",
    })
    mocker.patch("data_sources.fema.get_flood_zone", return_value={
        "zone": "X", "zone_subtype": "", "sfha": False,
        "risk_level": "Low/Moderate",
        "description": "Outside Special Flood Hazard Area",
        "base_flood_elevation": None,
        "source": "FEMA NFHL",
    })
    mocker.patch("data_sources.census.get_acs_data", return_value=None)

    from tools.location_tools import NeighborhoodTool
    result = NeighborhoodTool(llm=mock_llm).run("123 Main St, Austin, TX 78701")

    assert result["status"] == "success"
    user_msg = mock_llm.invoke.call_args[0][0][-1].content
    assert "88" in user_msg          # Walk Score value
    assert "Walk Score" in user_msg
    assert "Zone" in user_msg        # FEMA section header


def test_neighborhood_tool_injects_fema_high_risk(mock_llm, monkeypatch, mocker, tmp_path):
    """SFHA (high-risk) flood zone should be visible in the prompt."""
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mocker.patch("utils.geocode_address", return_value=(29.7604, -95.3698))
    mocker.patch("data_sources.walk_score.get_walk_score", return_value=None)
    mocker.patch("data_sources.fema.get_flood_zone", return_value={
        "zone": "AE", "zone_subtype": "", "sfha": True,
        "risk_level": "High",
        "description": "Special Flood Hazard Area — Base Flood Elevation determined",
        "base_flood_elevation": 45.0,
        "source": "FEMA NFHL",
    })
    mocker.patch("data_sources.census.get_acs_data", return_value=None)

    from tools.location_tools import NeighborhoodTool
    result = NeighborhoodTool(llm=mock_llm).run("456 Flood St, Houston, TX 77002")

    user_msg = mock_llm.invoke.call_args[0][0][-1].content
    assert "AE" in user_msg
    assert "High" in user_msg


def test_tools_degrade_gracefully_when_all_sources_unavailable(mock_llm, monkeypatch, mocker, tmp_path):
    """All tools must succeed even when every data source returns None."""
    monkeypatch.setattr("data_sources._cache._CACHE_DB", str(tmp_path / "ds.db"))
    monkeypatch.setattr("data_sources._cache._INIT_DONE", set())

    mocker.patch("data_sources.fred.get_mortgage_rates", return_value=None)
    mocker.patch("data_sources.hud.get_fair_market_rents", return_value=None)
    mocker.patch("data_sources.census.get_acs_data", return_value=None)
    mocker.patch("data_sources.walk_score.get_walk_score", return_value=None)
    mocker.patch("data_sources.fema.get_flood_zone", return_value=None)
    mocker.patch("utils.geocode_address", return_value=None)

    from tools.property_analysis import MortgageTool, RentalTool
    from tools.location_tools import NeighborhoodTool

    assert MortgageTool(llm=mock_llm).run("123 Main St")["status"] == "success"
    assert RentalTool(llm=mock_llm).run("123 Main St")["status"] == "success"
    assert NeighborhoodTool(llm=mock_llm).run("123 Main St")["status"] == "success"
