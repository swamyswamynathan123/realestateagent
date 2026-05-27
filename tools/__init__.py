"""
tools/__init__.py — Tool registry and factory function.
"""
from tools.validation import QuickTool, ScreenTool
from tools.property_analysis import CompsTool, RentalTool, MortgageTool
from tools.location_tools import NeighborhoodTool, MarketTool, ListingTool
from tools.investment_tools import InvestTool, FlipTool, CommercialTool, AnalyzeTool, CompareTool
from tools.additional_tools import STRTool, PropertyTaxTool

TOOL_REGISTRY: dict[str, type] = {
    "quick":        QuickTool,
    "screen":       ScreenTool,
    "comps":        CompsTool,
    "rental":       RentalTool,
    "mortgage":     MortgageTool,
    "neighborhood": NeighborhoodTool,
    "market":       MarketTool,
    "listing":      ListingTool,
    "invest":       InvestTool,
    "flip":         FlipTool,
    "commercial":   CommercialTool,
    "analyze":      AnalyzeTool,
    "compare":      CompareTool,
    "str":          STRTool,
    "tax":          PropertyTaxTool,
}


def get_tool(skill_name: str) -> "BaseRealEstateTool":  # type: ignore[name-defined]
    """Instantiate and return a tool by skill name."""
    cls = TOOL_REGISTRY.get(skill_name)
    if cls is None:
        raise ValueError(f"Unknown skill: '{skill_name}'. Valid skills: {list(TOOL_REGISTRY)}")
    return cls()
