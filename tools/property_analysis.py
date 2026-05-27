"""
tools/property_analysis.py — Comparable Sales, Rental/Cash Flow, Mortgage Calculator
"""
from __future__ import annotations
from tools.base import BaseRealEstateTool

# ── Comps ──────────────────────────────────────────────────────────────────────

COMPS_SYSTEM_PROMPT = """You are a real estate comparable sales analyst.

Live web-search data may be included in the user message under the heading
"## 🌐 Live Web Data". When that section is present:
- Extract real addresses, sale prices, square footages, and dates from it.
- Populate the comparable sales table with actual sold listings rather than
  placeholder values wherever the data allows.
- Note the data source in the footer as "Live web data (Tavily)" instead of
  "AI estimate".

When no live data is provided, rely on your training knowledge of the local
market to produce plausible estimates and note the source as "AI estimate".

Produce the analysis in this exact markdown format:

## Comparable Sales Analysis — {address}

### Subject Property Estimate
**Estimated Value:** $XXX,XXX
**Price per Sq Ft:** $XXX/sq ft
**Property Type:** [SFR / Condo / Townhouse / Multi-Family]
**Beds / Baths:** X / X
**Est. Square Footage:** X,XXX sq ft

### Comparable Sales (5 comps)
| # | Address | Sale Price | Sq Ft | $/Sq Ft | Distance | Days Ago | Similarity |
|---|---------|-----------|-------|---------|----------|----------|------------|
| 1 | [address] | $XXX,XXX | X,XXX | $XXX | X.X mi | XX | High/Med/Low |
| 2 | ... | ... | ... | ... | ... | ... | ... |
| 3 | ... | ... | ... | ... | ... | ... | ... |
| 4 | ... | ... | ... | ... | ... | ... | ... |
| 5 | ... | ... | ... | ... | ... | ... | ... |

### Adjustment Analysis
| Adjustment Factor | Direction | Est. Impact |
|-------------------|-----------|-------------|
| Size difference | +/- | $X,XXX |
| Age / condition | +/- | $X,XXX |
| Location premium | +/- | $X,XXX |
| Feature differences | +/- | $X,XXX |

**Adjusted Value Range:** $XXX,XXX – $XXX,XXX
**Median Comp Price:** $XXX,XXX
**Recommended List Price:** $XXX,XXX

### Market Context
**Current Market:** [Strong Seller's / Balanced / Buyer's]
**Avg Days on Market:** XX days
**List-to-Sale Ratio:** XX.X%

### Comp Quality Assessment
- **Data Quality:** XX/25 — [notes]
- **Price Alignment:** XX/25 — [notes]
- **Comp Relevance:** XX/25 — [notes]
- **Market Trend:** XX/25 — [notes]

**Score:** XX/100
**Grade:** [A+ through F]

*Source: [Live web data (Tavily) | AI estimate based on market knowledge]. Verify with licensed MLS data before making offers.*"""

# Real-estate listing portals likely to have recent sold data
_COMPS_DOMAINS = [
    "zillow.com", "redfin.com", "realtor.com",
    "trulia.com", "homes.com", "homelight.com",
]

# Absolute cap on total web context injected into the prompt (chars)
_MAX_WEB_CONTEXT_CHARS = 5_000


class CompsTool(BaseRealEstateTool):
    skill_name = "comps"
    system_prompt = COMPS_SYSTEM_PROMPT

    # ── Web data gathering ────────────────────────────────────────────────────

    def _fetch_live_comps(self, address: str) -> str:
        """
        Run up to three Tavily searches to gather live comparable sales data.

        Returns a formatted markdown block (possibly empty if Tavily is not
        configured or all searches return no results).
        """
        sections: list[str] = []

        # 1. Recently sold listings on the major portals
        sold = self._web_search(
            f'recently sold homes comparable to "{address}" sale price square footage 2024 2025',
            max_results=5,
            include_domains=_COMPS_DOMAINS,
        )
        if sold:
            sections.append(f"### Recently Sold Listings (Zillow / Redfin / Realtor)\n{sold}")

        # 2. Broader search — catches local news, county records, aggregators
        recent = self._web_search(
            f'"{address}" comparable home sales sold price per square foot recent',
            max_results=4,
        )
        if recent:
            sections.append(f"### Additional Comparable Sales Data\n{recent}")

        # 3. Local market context — median prices, days on market, trends
        market = self._web_search(
            f"real estate market median home price recently sold {address} 2024 2025 trends",
            max_results=3,
        )
        if market:
            sections.append(f"### Local Market Context\n{market}")

        if not sections:
            return ""

        body = "\n\n".join(sections)

        # Guard against runaway context size
        if len(body) > _MAX_WEB_CONTEXT_CHARS:
            body = body[:_MAX_WEB_CONTEXT_CHARS] + "\n\n*[web data truncated for length]*"

        return (
            "## 🌐 Live Web Data\n\n"
            "Use the real listing data below to populate the comparable sales table. "
            "Extract actual addresses, prices, and square footages where available.\n\n"
            + body
        )

    # ── Tool entry point ──────────────────────────────────────────────────────

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)

        # Assemble user message with optional live comps block
        user_msg = f"Property address: {address}"
        live_data = self._fetch_live_comps(address)
        if live_data:
            user_msg += f"\n\n{live_data}"

        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Rental ─────────────────────────────────────────────────────────────────────

RENTAL_SYSTEM_PROMPT = """You are a rental income and cash flow analysis specialist.
Provide detailed rental analysis using conservative assumptions.

## Rental & Cash Flow Analysis — {address}

### Rental Income Estimate
| Scenario | Monthly Rent | Annual Rent |
|----------|-------------|-------------|
| Conservative | $X,XXX | $XX,XXX |
| Moderate | $X,XXX | $XX,XXX |
| Optimistic | $X,XXX | $XX,XXX |

### Monthly Cash Flow (Moderate Scenario, 25% down, 30yr fixed ~7%)
| Item | Amount |
|------|--------|
| Gross Rent | $X,XXX |
| Vacancy (8%) | -$XXX |
| Effective Gross Income | $X,XXX |
| Mortgage (P&I) | -$X,XXX |
| Property Tax | -$XXX |
| Insurance | -$XXX |
| HOA | -$XXX |
| Maintenance (5%) | -$XXX |
| Property Mgmt (10%) | -$XXX |
| CapEx Reserve (5%) | -$XXX |
| **Net Cash Flow** | **$XXX** |

### Key Metrics
| Metric | Value | Benchmark |
|--------|-------|-----------|
| Cap Rate | X.X% | >=5% = good |
| Cash-on-Cash Return | X.X% | >=8% = good |
| Gross Rent Multiplier | XX | <12 = good |
| DSCR | X.XX | >=1.25 = good |
| Rent-to-Price Ratio | X.XX% | >=1% = good |

### Score Breakdown
- Cash Flow Strength: XX/25
- Cap Rate Quality: XX/20
- Cash-on-Cash Return: XX/20
- Rent Stability: XX/20
- DSCR: XX/15

**Score:** XX/100
**Grade:** [A+ through F]"""


class RentalTool(BaseRealEstateTool):
    skill_name = "rental"
    system_prompt = RENTAL_SYSTEM_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        user_msg = f"Property address: {address}"
        if kwargs.get("purchase_price"):
            user_msg += f"\nSale price: ${kwargs['purchase_price']:,}"
        if kwargs.get("hoa_fees"):
            user_msg += f"\nMonthly HOA fees: ${kwargs['hoa_fees']:,}/mo (use this exact figure in the cash flow table)"
        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Mortgage ───────────────────────────────────────────────────────────────────

MORTGAGE_SYSTEM_PROMPT = """You are a mortgage calculator and affordability specialist.

## Mortgage Analysis — {address}

### Loan Scenarios
Assume estimated purchase price from comps. Show 4 down payment scenarios (5%, 10%, 20%, 25%).
Assume current 30yr fixed rate ~7.0%, 15yr ~6.3%.

| Down Payment | Loan Amount | Monthly P&I | Total Interest | Monthly PITI |
|-------------|-------------|-------------|----------------|--------------|
| 5% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |
| 10% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |
| 20% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |
| 25% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |

### Affordability Thresholds (28/36 Rule)
| Income Needed | For 5% Down | For 20% Down |
|--------------|-------------|--------------|
| Monthly (28% housing) | $X,XXX | $X,XXX |
| Annual | $XX,XXX | $XX,XXX |

### Loan Program Eligibility
- **Conventional:** [Yes/Likely/No] — [reason]
- **FHA (3.5% down):** [Yes/Likely/No] — [reason]
- **VA (0% down):** Possible — requires veteran status
- **Jumbo:** [Yes/No] — [reason]

### Mortgage Summary
[2-3 sentence summary]"""


class MortgageTool(BaseRealEstateTool):
    skill_name = "mortgage"
    system_prompt = MORTGAGE_SYSTEM_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        purchase_price = kwargs.get("purchase_price")
        hoa_fees = kwargs.get("hoa_fees")
        prompt = self.system_prompt.replace("{address}", address)
        user_msg = f"Property address: {address}"
        if purchase_price:
            user_msg += f"\nEstimated purchase price: ${purchase_price:,}"
        if hoa_fees:
            user_msg += f"\nMonthly HOA fees: ${hoa_fees:,}/mo (include in PITI calculations)"
        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))
