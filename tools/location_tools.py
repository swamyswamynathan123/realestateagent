"""
tools/location_tools.py — Neighborhood Analysis, Market Conditions, MLS Listing
"""
from __future__ import annotations
from tools.base import BaseRealEstateTool

# ── Neighborhood ───────────────────────────────────────────────────────────────

NEIGHBORHOOD_PROMPT = """You are a neighborhood analysis expert.

Real data may be included under "## 🏛️ Live Real Data". When present:
- Use the exact Walk Score, Transit Score, and Bike Score values — do NOT estimate them.
- Use the FEMA flood zone in the safety section and note it as a real risk factor.
- Use Census demographics (population, income, owner/renter mix) for the Growth Indicators.
- Note sources inline: "(Walk Score®)", "(FEMA NFHL)", "(US Census ACS)".

When no real data is provided, use your training knowledge and note "AI estimate".

## Neighborhood Analysis — {address}

### Location Scores (0-20 each)
| Category | Score | Key Factors |
|----------|-------|-------------|
| Schools | XX/20 | [school names, ratings] |
| Safety | XX/20 | [crime index, flood zone, trends] |
| Walkability & Transit | XX/20 | [Walk Score XX, Transit Score XX, Bike Score XX] |
| Amenities | XX/20 | [grocery, dining, parks] |
| Growth Trajectory | XX/20 | [development, jobs, population] |

### School District
**District:** [Name]
**Elementary:** [Name] — Rating X/10
**Middle:** [Name] — Rating X/10
**High School:** [Name] — Rating X/10

### Safety Overview
**Crime Index:** [Low/Moderate/High] relative to national avg
**Flood Zone:** [FEMA zone code] — [risk level]
**Trend:** [Improving/Stable/Worsening]

### Walkability
**Walk Score:** XX/100 — [description]
**Transit Score:** XX/100 — [description]
**Bike Score:** XX/100 — [description]

### Amenities Within 1 Mile
- Grocery: [nearest stores]
- Dining: [restaurant density]
- Parks: [nearest parks]
- Healthcare: [nearest hospital/clinic]

### Demographic Snapshot
- Population (ZIP): [XX,XXX]
- Median Household Income: $XX,XXX/yr
- Owner-Occupied: XX% | Renter-Occupied: XX%

### Growth Indicators
[2-3 sentences on development pipeline, job growth, population trends]

**Score:** XX/100
**Grade:** [A+ through F]

*Source: [Walk Score® / FEMA NFHL / US Census ACS | AI estimate]*"""


class NeighborhoodTool(BaseRealEstateTool):
    skill_name = "neighborhood"
    system_prompt = NEIGHBORHOOD_PROMPT

    def _fetch_real_data(self, address: str) -> str:
        """Fetch Walk Score, FEMA flood zone, and Census demographics."""
        sections: list[str] = []

        # Geocode once — needed for Walk Score and FEMA
        try:
            from utils import geocode_address
            coords = geocode_address(address)
            lat, lon = coords if coords else (None, None)
        except Exception:
            lat, lon = None, None

        # Walk Score
        if lat and lon:
            try:
                from data_sources.walk_score import get_walk_score
                ws = get_walk_score(address, lat, lon)
                if ws:
                    lines = ["### Walk Score® (official scores)"]
                    if ws.get("walk_score") is not None:
                        lines.append(f"- **Walk Score: {ws['walk_score']}/100** — {ws.get('walk_desc', '')}")
                    if ws.get("transit_score") is not None:
                        lines.append(f"- **Transit Score: {ws['transit_score']}/100** — {ws.get('transit_desc', '')}")
                    if ws.get("bike_score") is not None:
                        lines.append(f"- **Bike Score: {ws['bike_score']}/100** — {ws.get('bike_desc', '')}")
                    lines.append(f"- *Source: {ws.get('source', 'Walk Score®')}*")
                    sections.append("\n".join(lines))
            except Exception:
                pass

        # FEMA flood zone
        if lat and lon:
            try:
                from data_sources.fema import get_flood_zone
                flood = get_flood_zone(lat, lon)
                if flood:
                    risk_icon = "🔴" if flood["sfha"] else "🟢"
                    lines = [
                        "### FEMA Flood Zone (National Flood Hazard Layer)",
                        f"- **Flood Zone: {flood['zone']}** — {flood['description']}",
                        f"- **Risk Level: {risk_icon} {flood['risk_level']}**",
                        f"- **SFHA (Special Flood Hazard Area):** "
                        f"{'Yes — federal flood insurance required for backed loans' if flood['sfha'] else 'No'}",
                    ]
                    if flood.get("base_flood_elevation"):
                        lines.append(f"- Base Flood Elevation: {flood['base_flood_elevation']} ft NAVD")
                    lines.append(f"- *Source: {flood['source']}*")
                    sections.append("\n".join(lines))
            except Exception:
                pass

        # Census ACS demographics
        try:
            from data_sources.census import get_acs_data
            acs = get_acs_data(address)
            if acs:
                lines = [f"### US Census ACS Demographics — ZIP {acs['zip']}"]
                if acs.get("population"):
                    lines.append(f"- Population: **{acs['population']:,}**")
                if acs.get("median_home_value"):
                    lines.append(f"- Median home value: **${acs['median_home_value']:,}**")
                if acs.get("median_income"):
                    lines.append(f"- Median household income: **${acs['median_income']:,}/yr**")
                own = acs.get("owner_occupied") or 0
                rnt = acs.get("renter_occupied") or 0
                if own + rnt > 0:
                    owner_pct = int(own / (own + rnt) * 100)
                    renter_pct = 100 - owner_pct
                    lines.append(f"- Owner-occupied: **{owner_pct}%** | Renter-occupied: **{renter_pct}%**")
                lines.append(f"- *Source: {acs['source']}*")
                sections.append("\n".join(lines))
        except Exception:
            pass

        if not sections:
            return ""

        return (
            "## 🏛️ Live Real Data\n\n"
            "Use the real data below in the neighborhood analysis. "
            "Walk Scores and FEMA flood zone are official published figures.\n\n"
            + "\n\n".join(sections)
        )

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        user_msg = f"Property address: {address}"

        real_data = self._fetch_real_data(address)
        if real_data:
            user_msg += f"\n\n{real_data}"

        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Market ─────────────────────────────────────────────────────────────────────

MARKET_PROMPT = """You are a real estate market analyst.

Live web-search data may be included in the user message under the heading
"## 🌐 Live Market Data". When that section is present:
- Extract real figures for median price, days on market, inventory, YoY change,
  and list-to-sale ratio from the search results and use them in the report.
- Cite the data source (e.g. "per Redfin, May 2025") inline where relevant.
- Note the footer as "Live web data (Tavily)" instead of "AI estimate".

When no live data is provided, rely on your training knowledge and note the
footer as "AI estimate — verify with current MLS data".

Produce the analysis in this exact markdown format:

## Market Conditions — {address}

### Market Classification
**Market Type:** [Strong Seller's / Seller's / Balanced / Buyer's / Strong Buyer's]
**Median Days on Market:** XX days
**List-to-Sale Ratio:** XX.X%
**Active Inventory:** [Low / Normal / High] — X.X months of supply
**Market Momentum:** [Heating / Stable / Cooling]

### Market Score Breakdown
| Dimension | Score | Detail |
|-----------|-------|--------|
| Price Trends | XX/25 | [YoY appreciation %, trajectory] |
| Supply & Demand | XX/20 | [months of inventory, absorption rate] |
| Economic Drivers | XX/20 | [job growth, major employers, GDP] |
| Rental Market | XX/15 | [vacancy rate, rent growth YoY] |
| Growth Catalysts | XX/20 | [infrastructure, migration, permits] |

### Price Trend (12 months)
**Median Home Price:** $XXX,XXX
**YoY Change:** +X.X%
**Price per Sq Ft:** $XXX (YoY: +X.X%)
**Forecast (12 mo):** +X.X% to +X.X%

### Supply & Demand
**Active Listings:** ~X,XXX
**New Listings (mo):** ~XXX
**Absorption Rate:** XX%
**Months of Supply:** X.X

### Economic Snapshot
**Unemployment Rate:** X.X%
**Top Employers:** [employer 1], [employer 2], [employer 3]
**Population Trend:** [Growing / Stable / Declining] (+X.X% YoY)

### Key Market Drivers
1. [driver 1 — be specific, cite data if available]
2. [driver 2]
3. [driver 3]

### Risks & Headwinds
1. [risk 1]
2. [risk 2]

**Score:** XX/100
**Grade:** [A+ through F]

*Source: [Live web data (Tavily) | AI estimate — verify with current MLS data]*"""

# Sources most likely to have current market statistics
_MARKET_DOMAINS = [
    "redfin.com", "zillow.com", "realtor.com",
    "nar.realtor", "housingwire.com", "themortgagereports.com",
]

_MAX_MARKET_CONTEXT_CHARS = 5_000


class MarketTool(BaseRealEstateTool):
    skill_name = "market"
    system_prompt = MARKET_PROMPT

    # ── Web data gathering ────────────────────────────────────────────────────

    def _fetch_market_data(self, address: str) -> str:
        """
        Run up to three Tavily searches for live market-condition data.

        Returns a formatted markdown block, or '' if Tavily is unavailable.
        """
        sections: list[str] = []

        # 1. Current market stats from real-estate portals
        stats = self._web_search(
            f"real estate market conditions {address} median home price days on market"
            f" inventory 2024 2025",
            max_results=5,
            include_domains=_MARKET_DOMAINS,
        )
        if stats:
            sections.append(f"### Market Statistics (Redfin / Zillow / NAR)\n{stats}")

        # 2. Local price trends and YoY appreciation
        trends = self._web_search(
            f"home price trends {address} year over year appreciation forecast 2025",
            max_results=4,
        )
        if trends:
            sections.append(f"### Price Trends & Forecast\n{trends}")

        # 3. Economic drivers — jobs, migration, development
        economy = self._web_search(
            f"{address} real estate market economic outlook job growth population"
            f" housing demand 2025",
            max_results=3,
        )
        if economy:
            sections.append(f"### Economic & Demand Drivers\n{economy}")

        if not sections:
            return ""

        body = "\n\n".join(sections)
        if len(body) > _MAX_MARKET_CONTEXT_CHARS:
            body = body[:_MAX_MARKET_CONTEXT_CHARS] + "\n\n*[web data truncated for length]*"

        return (
            "## 🌐 Live Market Data\n\n"
            "Use the figures below to populate the market analysis. Extract median price, "
            "days on market, YoY change, and inventory levels where available.\n\n"
            + body
        )

    # ── Tool entry point ──────────────────────────────────────────────────────

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)

        user_msg = f"Property address: {address}"
        live_data = self._fetch_market_data(address)
        if live_data:
            user_msg += f"\n\n{live_data}"

        try:
            output = self._call_llm(prompt, user_msg)
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
