import pytest
from unittest.mock import MagicMock


# ── Task 4: Base tool tests ────────────────────────────────────────────────────

def test_base_tool_calls_llm(mock_llm):
    from tools.base import BaseRealEstateTool

    class ConcreteTestTool(BaseRealEstateTool):
        skill_name = "test"
        system_prompt = "You are a test agent."

        def run(self, address: str, **kwargs) -> dict:
            output = self._call_llm(self.system_prompt, f"Analyze: {address}")
            return self._success_result(address, output)

    tool = ConcreteTestTool(llm=mock_llm)
    result = tool.run("123 Main St, Austin TX")
    assert result["status"] == "success"
    assert "Mock Analysis" in result["output"]
    mock_llm.invoke.assert_called_once()


def test_base_tool_handles_llm_error(mock_llm):
    from tools.base import BaseRealEstateTool

    mock_llm.invoke.side_effect = Exception("API timeout")

    class FailingTool(BaseRealEstateTool):
        skill_name = "failing"
        system_prompt = "You are a test agent."

        def run(self, address: str, **kwargs) -> dict:
            try:
                output = self._call_llm(self.system_prompt, address)
                return self._success_result(address, output)
            except Exception as e:
                return self._error_result(address, str(e))

    tool = FailingTool(llm=mock_llm)
    result = tool.run("123 Main St")
    assert result["status"] == "error"
    assert "API timeout" in result["error"]


def test_extract_score_parses_x_of_100(mock_llm):
    from tools.base import BaseRealEstateTool

    class MinimalTool(BaseRealEstateTool):
        skill_name = "minimal"
        def run(self, address, **kw): return {}

    tool = MinimalTool(llm=mock_llm)
    assert tool._extract_score("Score: 75/100") == 75
    assert tool._extract_score("**Score:** 82/100") == 82
    assert tool._extract_score("no score here") is None


def test_score_to_grade(mock_llm):
    from tools.base import BaseRealEstateTool

    class MinimalTool(BaseRealEstateTool):
        skill_name = "minimal"
        def run(self, address, **kw): return {}

    tool = MinimalTool(llm=mock_llm)
    assert tool._score_to_grade(90) == "A+"
    assert tool._score_to_grade(75) == "A"
    assert tool._score_to_grade(60) == "B"
    assert tool._score_to_grade(45) == "C"
    assert tool._score_to_grade(30) == "D"
    assert tool._score_to_grade(10) == "F"
    assert tool._score_to_grade(None) is None


# ── Task 5: Validation tool tests ──────────────────────────────────────────────

def test_quick_tool_returns_success(mock_llm):
    from tools.validation import QuickTool
    tool = QuickTool(llm=mock_llm)
    result = tool.run("123 Main St, Austin TX")
    assert result["skill"] == "quick"
    assert result["status"] == "success"
    assert len(result["output"]) > 10


def test_quick_tool_returns_error_on_llm_failure(mock_llm):
    mock_llm.invoke.side_effect = Exception("rate limit")
    from tools.validation import QuickTool
    tool = QuickTool(llm=mock_llm)
    result = tool.run("123 Main St, Austin TX")
    assert result["status"] == "error"
    assert "rate limit" in result["error"]


def test_screen_tool_returns_success(mock_llm):
    from tools.validation import ScreenTool
    tool = ScreenTool(llm=mock_llm)
    result = tool.run("123 Main St, Austin TX")
    assert result["skill"] == "screen"
    assert result["status"] == "success"
    assert "validation_passed" in result


def test_screen_tool_sets_validation_passed_true(mock_llm):
    from tools.validation import ScreenTool
    tool = ScreenTool(llm=mock_llm)
    result = tool.run("123 Main St, Austin TX")
    # mock returns "# Mock Analysis..." which does NOT start with VALIDATION_FAILED
    assert result["validation_passed"] is True


def test_screen_tool_detects_validation_failed(mock_llm):
    mock_llm.invoke.return_value = MagicMock(
        content="VALIDATION_FAILED: Address not recognizable."
    )
    from tools.validation import ScreenTool
    tool = ScreenTool(llm=mock_llm)
    result = tool.run("asdfghjkl")
    assert result["validation_passed"] is False


# ── Task 6: Property analysis tool tests ───────────────────────────────────────

def test_comps_tool(mock_llm):
    from tools.property_analysis import CompsTool
    result = CompsTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "comps"
    assert result["status"] == "success"


# ── Comp-count helpers ────────────────────────────────────────────────────────

_FULL_COMPS = """\
## Comparable Sales Analysis — 123 Main St

### Comparable Sales (5 comps)
| # | Address | Sale Price | Sq Ft | $/Sq Ft | Distance | Days Ago | Similarity |
|---|---------|-----------|-------|---------|----------|----------|------------|
| 1 | 100 Oak Ave | $420,000 | 1,800 | $233 | 0.3 mi | 14 | High |
| 2 | 200 Elm St  | $405,000 | 1,750 | $231 | 0.5 mi | 30 | High |
| 3 | 300 Pine Rd | $435,000 | 1,900 | $229 | 0.7 mi | 45 | Med  |
| 4 | 400 Maple Dr| $398,000 | 1,700 | $234 | 1.1 mi | 60 | Med  |
| 5 | 500 Cedar Ln| $450,000 | 1,950 | $231 | 1.4 mi | 75 | Low  |

**Score:** 78/100
"""

_PARTIAL_COMPS = """\
## Comparable Sales Analysis — 123 Main St

### Comparable Sales (5 comps)
| # | Address | Sale Price | Sq Ft | $/Sq Ft | Distance | Days Ago | Similarity |
|---|---------|-----------|-------|---------|----------|----------|------------|
| 1 | 100 Oak Ave | $420,000 | 1,800 | $233 | 0.3 mi | 14 | High |
| 2 | 200 Elm St  | $405,000 | 1,750 | $231 | 0.5 mi | 30 | High |

**Score:** 60/100
"""


def test_count_comp_rows_full():
    from tools.property_analysis import CompsTool
    assert CompsTool._count_comp_rows(_FULL_COMPS) == 5


def test_count_comp_rows_partial():
    from tools.property_analysis import CompsTool
    assert CompsTool._count_comp_rows(_PARTIAL_COMPS) == 2


def test_count_comp_rows_empty():
    from tools.property_analysis import CompsTool
    assert CompsTool._count_comp_rows("No table here.") == 0


def test_ensure_five_comps_already_complete(mock_llm, mocker):
    """If the output already has 5 rows, no second LLM call is made."""
    mocker.patch("tools.base.BaseRealEstateTool._get_search_cache", return_value=None)
    from tools.property_analysis import CompsTool
    tool = CompsTool(llm=mock_llm)
    result = tool._ensure_five_comps(_FULL_COMPS, "123 Main St")
    assert result == _FULL_COMPS
    mock_llm.invoke.assert_not_called()


def test_ensure_five_comps_triggers_fix_call(mock_llm):
    """If fewer than 5 rows are found, a second LLM call is made to fix it."""
    from unittest.mock import MagicMock
    # First call (fix): return a report with 5 rows
    fix_response = MagicMock(content=_FULL_COMPS)
    mock_llm.invoke.return_value = fix_response

    from tools.property_analysis import CompsTool
    tool = CompsTool(llm=mock_llm)
    result = tool._ensure_five_comps(_PARTIAL_COMPS, "123 Main St")

    # The fix call must have been made
    mock_llm.invoke.assert_called_once()
    assert CompsTool._count_comp_rows(result) == 5


def test_comps_tool_fix_call_on_short_output(mock_llm, monkeypatch, mocker):
    """End-to-end: when first LLM response is sparse, a fix call tops it up."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    mocker.patch("tools.base.BaseRealEstateTool._get_search_cache", return_value=None)

    from unittest.mock import MagicMock, call
    # First call returns only 2 rows; second (fix) call returns all 5
    mock_llm.invoke.side_effect = [
        MagicMock(content=_PARTIAL_COMPS),
        MagicMock(content=_FULL_COMPS),
    ]

    from tools.property_analysis import CompsTool
    result = CompsTool(llm=mock_llm).run("123 Main St, Austin TX")

    assert result["status"] == "success"
    assert mock_llm.invoke.call_count == 2   # initial + fix
    assert CompsTool._count_comp_rows(result["output"]) == 5


def test_comps_tool_no_tavily_key_no_web_data(mock_llm, monkeypatch, mocker):
    """Without a Tavily key the tool succeeds using LLM knowledge only."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    # Also bypass the search cache so any pre-existing cached data doesn't leak in
    mocker.patch("tools.base.BaseRealEstateTool._get_search_cache", return_value=None)
    from tools.property_analysis import CompsTool
    result = CompsTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["status"] == "success"
    # LLM was called exactly once — no search made
    assert mock_llm.invoke.call_count == 1
    # No live-data header injected
    call_args = mock_llm.invoke.call_args[0][0]
    user_msg = call_args[-1].content  # last message is HumanMessage
    assert "🌐 Live Web Data" not in user_msg


def test_comps_tool_injects_tavily_results(mock_llm, monkeypatch, mocker):
    """With a Tavily key the tool injects search results into the LLM prompt."""
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    fake_results = {
        "results": [
            {
                "title": "456 Oak Ave Austin TX — Sold $450,000",
                "content": "3 bed 2 bath 1,800 sq ft sold 30 days ago for $450,000 ($250/sqft)",
                "url": "https://www.zillow.com/fake",
            }
        ]
    }
    mocker.patch("tavily.TavilyClient.search", return_value=fake_results)
    # Bypass the search cache so the mocked Tavily response is always used
    mocker.patch("tools.base.BaseRealEstateTool._get_search_cache", return_value=None)
    from tools.property_analysis import CompsTool
    result = CompsTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["status"] == "success"
    call_args = mock_llm.invoke.call_args[0][0]
    user_msg = call_args[-1].content
    assert "🌐 Live Web Data" in user_msg
    assert "456 Oak Ave" in user_msg


def test_search_cache_prevents_duplicate_tavily_calls(mock_llm, monkeypatch, mocker, tmp_path):
    """Search cache hit: second run must not call Tavily again."""
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    fake_results = {
        "results": [
            {
                "title": "789 Pine St — Sold $380,000",
                "content": "2 bed 1 bath 1,200 sq ft sold for $380,000",
                "url": "https://www.redfin.com/fake",
            }
        ]
    }
    tavily_mock = mocker.patch("tavily.TavilyClient.search", return_value=fake_results)

    # Use an isolated temp cache so test state doesn't bleed
    from cache import SQLiteCache
    test_cache = SQLiteCache(db_path=str(tmp_path / "test_search.db"))
    mocker.patch(
        "tools.base.BaseRealEstateTool._get_search_cache",
        return_value=test_cache,
    )

    from tools.property_analysis import CompsTool
    tool = CompsTool(llm=mock_llm)

    # First run: Tavily is called (cache miss)
    tool.run("789 Pine St, Denver CO")
    calls_after_first = tavily_mock.call_count
    assert calls_after_first > 0, "Tavily should have been called on the first run"

    # Second run: search cache hits — Tavily call count must not increase
    mock_llm.reset_mock()
    tool.run("789 Pine St, Denver CO")
    assert tavily_mock.call_count == calls_after_first, (
        "Tavily was called again on the second run; search cache did not work"
    )
    # But the LLM IS called again (LLM cache is separate and keyed on prompt,
    # which includes the Tavily text — stable now, so a real run would hit it too)
    assert mock_llm.invoke.call_count > 0


def test_rental_tool(mock_llm):
    from tools.property_analysis import RentalTool
    result = RentalTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "rental"
    assert result["status"] == "success"


def test_mortgage_tool_with_price(mock_llm):
    from tools.property_analysis import MortgageTool
    result = MortgageTool(llm=mock_llm).run("123 Main St, Austin TX", purchase_price=400000)
    assert result["skill"] == "mortgage"
    assert result["status"] == "success"
    # Verify the purchase price was included in the LLM call
    call_args = mock_llm.invoke.call_args
    user_message = call_args[0][0][-1].content  # last message is HumanMessage
    assert "400,000" in user_message


def test_rental_tool_with_price_and_hoa(mock_llm):
    from tools.property_analysis import RentalTool
    result = RentalTool(llm=mock_llm).run("123 Main St, Austin TX", purchase_price=350000, hoa_fees=250)
    assert result["status"] == "success"
    call_args = mock_llm.invoke.call_args
    user_message = call_args[0][0][-1].content
    assert "350,000" in user_message
    assert "250" in user_message


def test_mortgage_tool_with_price_and_hoa(mock_llm):
    from tools.property_analysis import MortgageTool
    result = MortgageTool(llm=mock_llm).run("123 Main St, Austin TX", purchase_price=400000, hoa_fees=300)
    assert result["status"] == "success"
    call_args = mock_llm.invoke.call_args
    user_message = call_args[0][0][-1].content
    assert "400,000" in user_message
    assert "300" in user_message


def test_invest_tool_with_price(mock_llm):
    from tools.investment_tools import InvestTool
    result = InvestTool(llm=mock_llm).run("123 Main St, Austin TX", purchase_price=500000)
    assert result["status"] == "success"
    call_args = mock_llm.invoke.call_args
    user_message = call_args[0][0][-1].content
    assert "500,000" in user_message


def test_flip_tool_with_price(mock_llm):
    from tools.investment_tools import FlipTool
    result = FlipTool(llm=mock_llm).run("123 Main St, Austin TX", purchase_price=275000)
    assert result["status"] == "success"
    call_args = mock_llm.invoke.call_args
    user_message = call_args[0][0][-1].content
    assert "275,000" in user_message


# ── Task 7: Location & market tool tests ───────────────────────────────────────

def test_neighborhood_tool(mock_llm):
    from tools.location_tools import NeighborhoodTool
    result = NeighborhoodTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "neighborhood"
    assert result["status"] == "success"


def test_market_tool(mock_llm):
    from tools.location_tools import MarketTool
    result = MarketTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "market"
    assert result["status"] == "success"


def test_market_tool_no_tavily_key(mock_llm, monkeypatch, mocker):
    """Without a Tavily key the market tool uses LLM knowledge only."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    mocker.patch("tools.base.BaseRealEstateTool._get_search_cache", return_value=None)
    from tools.location_tools import MarketTool
    result = MarketTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["status"] == "success"
    user_msg = mock_llm.invoke.call_args[0][0][-1].content
    assert "🌐 Live Market Data" not in user_msg


def test_market_tool_injects_tavily_results(mock_llm, monkeypatch, mocker):
    """With a Tavily key, live market stats are injected into the LLM prompt."""
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    fake_results = {
        "results": [
            {
                "title": "Austin TX Housing Market — May 2025",
                "content": "Median home price $485,000, down 3% YoY. Avg 28 days on market."
                           " 3.2 months of supply. List-to-sale ratio 97.5%.",
                "url": "https://www.redfin.com/city/30818/TX/Austin/housing-market",
            }
        ]
    }
    mocker.patch("tavily.TavilyClient.search", return_value=fake_results)
    mocker.patch("tools.base.BaseRealEstateTool._get_search_cache", return_value=None)
    from tools.location_tools import MarketTool
    result = MarketTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["status"] == "success"
    user_msg = mock_llm.invoke.call_args[0][0][-1].content
    assert "🌐 Live Market Data" in user_msg
    assert "485,000" in user_msg


def test_market_tool_search_cache_prevents_duplicate_calls(mock_llm, monkeypatch, mocker, tmp_path):
    """Second run with the same address must not call Tavily again."""
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    fake_results = {
        "results": [{"title": "Denver Market", "content": "Median $550k", "url": "http://x.com"}]
    }
    tavily_mock = mocker.patch("tavily.TavilyClient.search", return_value=fake_results)

    from cache import SQLiteCache
    test_cache = SQLiteCache(db_path=str(tmp_path / "market_test.db"))
    mocker.patch("tools.base.BaseRealEstateTool._get_search_cache", return_value=test_cache)

    from tools.location_tools import MarketTool
    tool = MarketTool(llm=mock_llm)

    tool.run("456 Elm St, Denver CO")
    calls_after_first = tavily_mock.call_count
    assert calls_after_first > 0

    mock_llm.reset_mock()
    tool.run("456 Elm St, Denver CO")
    assert tavily_mock.call_count == calls_after_first, "Tavily called again despite search cache"


def test_listing_tool(mock_llm):
    from tools.location_tools import ListingTool
    result = ListingTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "listing"
    assert result["status"] == "success"


# ── Task 8: Investment tool tests ──────────────────────────────────────────────

def test_invest_tool(mock_llm):
    from tools.investment_tools import InvestTool
    result = InvestTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "invest"
    assert result["status"] == "success"


def test_flip_tool(mock_llm):
    from tools.investment_tools import FlipTool
    result = FlipTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "flip"
    assert result["status"] == "success"


def test_commercial_tool(mock_llm):
    from tools.investment_tools import CommercialTool
    result = CommercialTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "commercial"
    assert result["status"] == "success"


def test_analyze_tool(mock_llm):
    from tools.investment_tools import AnalyzeTool
    result = AnalyzeTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "analyze"
    assert result["status"] == "success"


def test_compare_tool(mock_llm):
    from tools.investment_tools import CompareTool
    result = CompareTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["skill"] == "compare"
    assert result["status"] == "success"


def test_tool_registry_has_all_skills():
    from tools import TOOL_REGISTRY, get_tool
    import config
    for skill in config.ALL_SKILLS:
        assert skill in TOOL_REGISTRY, f"Missing skill: {skill}"

def test_get_tool_raises_on_unknown():
    from tools import get_tool
    with pytest.raises(ValueError, match="Unknown skill"):
        get_tool("nonexistent_skill")
