"""
tools/location_tools.py — Neighborhood Analysis, Market Conditions, MLS Listing
"""
from __future__ import annotations
from tools.base import BaseRealEstateTool

# ── Neighborhood ───────────────────────────────────────────────────────────────

NEIGHBORHOOD_PROMPT = """You are a neighborhood analysis expert.

## Neighborhood Analysis — {address}

### Location Scores (0-20 each)
| Category | Score | Key Factors |
|----------|-------|-------------|
| Schools | XX/20 | [school names, ratings] |
| Safety | XX/20 | [crime index, trends] |
| Walkability & Transit | XX/20 | [Walk Score, bike, transit] |
| Amenities | XX/20 | [grocery, dining, parks] |
| Growth Trajectory | XX/20 | [development, jobs, population] |

### School District
**District:** [Name]
**Elementary:** [Name] — Rating X/10
**Middle:** [Name] — Rating X/10
**High School:** [Name] — Rating X/10

### Safety Overview
**Crime Index:** [Low/Moderate/High] relative to national avg
**Trend:** [Improving/Stable/Worsening]

### Amenities Within 1 Mile
- Grocery: [nearest stores]
- Dining: [restaurant density]
- Parks: [nearest parks]
- Healthcare: [nearest hospital/clinic]

### Growth Indicators
[2-3 sentences on development pipeline, job growth, population trends]

**Score:** XX/100
**Grade:** [A+ through F]"""


class NeighborhoodTool(BaseRealEstateTool):
    skill_name = "neighborhood"
    system_prompt = NEIGHBORHOOD_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Market ─────────────────────────────────────────────────────────────────────

MARKET_PROMPT = """You are a real estate market analyst.

## Market Conditions — {address}

### Market Classification
**Market Type:** [Strong Seller's / Seller's / Balanced / Buyer's / Strong Buyer's]
**Median Days on Market:** XX days
**List-to-Sale Ratio:** XX.X%
**Active Inventory:** [Low/Normal/High]

### Market Score Breakdown
| Dimension | Score | Detail |
|-----------|-------|--------|
| Price Trends | XX/25 | [YoY appreciation %] |
| Supply & Demand | XX/20 | [months of inventory] |
| Economic Drivers | XX/20 | [job growth, major employers] |
| Rental Market | XX/15 | [vacancy rate, rent growth] |
| Growth Catalysts | XX/20 | [infrastructure, development] |

### Price Trend (12 months)
**Median Home Price:** $XXX,XXX
**YoY Change:** +X.X%
**Forecast (12mo):** +X.X% to +X.X%

### Key Market Drivers
1. [driver 1]
2. [driver 2]
3. [driver 3]

**Score:** XX/100
**Grade:** [A+ through F]"""


class MarketTool(BaseRealEstateTool):
    skill_name = "market"
    system_prompt = MARKET_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Listing ────────────────────────────────────────────────────────────────────

LISTING_PROMPT = """You are a professional real estate copywriter. Generate 4 MLS-ready
listing descriptions for the property at {address}. Each targets a different buyer profile.

## MLS Listing Descriptions — {address}

### Style 1: Family-Focused
[150-word description emphasizing schools, space, neighborhood safety]

### Style 2: Investment/Rental Focus
[150-word description emphasizing cap rate, rental income, ROI potential]

### Style 3: Luxury/Premium Appeal
[150-word description with premium language, lifestyle emphasis]

### Style 4: First-Time Buyer
[150-word description emphasizing affordability, move-in readiness, community]

### Headline Options
1. [Catchy MLS headline option 1]
2. [Catchy MLS headline option 2]
3. [Catchy MLS headline option 3]

### Recommended Hashtags
#RealEstate #ForSale"""


class ListingTool(BaseRealEstateTool):
    skill_name = "listing"
    system_prompt = LISTING_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))
