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


def test_comps_tool_no_tavily_key_no_web_data(mock_llm, monkeypatch):
    """Without a Tavily key the tool should succeed using LLM knowledge only."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
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
    # Patch TavilyClient.search to return a canned result
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
    from tools.property_analysis import CompsTool
    result = CompsTool(llm=mock_llm).run("123 Main St, Austin TX")
    assert result["status"] == "success"
    call_args = mock_llm.invoke.call_args[0][0]
    user_msg = call_args[-1].content
    assert "🌐 Live Web Data" in user_msg
    assert "456 Oak Ave" in user_msg


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
