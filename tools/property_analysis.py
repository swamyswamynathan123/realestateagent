"""
tools/property_analysis.py — Comparable Sales, Rental/Cash Flow, Mortgage Calculator
"""
from __future__ import annotations
import re
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

CRITICAL REQUIREMENT — THE COMPARABLE SALES TABLE MUST ALWAYS CONTAIN EXACTLY
5 DATA ROWS (rows 1 through 5). This is non-negotiable:
- If the web search data contains fewer than 5 sold listings, fill the remaining
  rows using your training knowledge of comparable properties in the same area.
- Never leave a row as "..." or skip a row number.
- Never produce a table with fewer than 5 completed data rows.

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
| 2 | [address] | $XXX,XXX | X,XXX | $XXX | X.X mi | XX | High/Med/Low |
| 3 | [address] | $XXX,XXX | X,XXX | $XXX | X.X mi | XX | High/Med/Low |
| 4 | [address] | $XXX,XXX | X,XXX | $XXX | X.X mi | XX | High/Med/Low |
| 5 | [address] | $XXX,XXX | X,XXX | $XXX | X.X mi | XX | High/Med/Low |

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

    # ── Comp-count validation ─────────────────────────────────────────────────

    @staticmethod
    def _count_comp_rows(text: str) -> int:
        """Count completed data rows in the Comparable Sales table.

        Looks for rows that start with ``| 1 |`` through ``| 9 |`` so it is
        robust to different column counts and formatting variations.
        """
        # Primary: count explicitly numbered rows (| 1 | … | 5 |)
        numbered = re.findall(r"^\|\s*[1-9]\s*\|", text, re.MULTILINE)
        if numbered:
            return len(numbered)

        # Fallback: find the comps section and count non-header pipe rows
        section = re.search(
            r"### Comparable Sales.*?(?=\n###|\Z)", text, re.DOTALL | re.IGNORECASE
        )
        if not section:
            return 0
        data_rows = [
            ln for ln in section.group().splitlines()
            if ln.strip().startswith("|")
            and "---" not in ln
            and not re.search(r"address|sale price|similarity|#", ln, re.IGNORECASE)
        ]
        return len(data_rows)

    _FIX_SYSTEM = (
        "You are a real estate comparable sales analyst completing an incomplete report. "
        "The user will provide a partial comps report. Your ONLY job is to return the "
        "complete report with exactly 5 rows in the Comparable Sales table. "
        "Keep every other section unchanged. "
        "Fill missing rows using your training knowledge of comparable properties "
        "in the same area — never leave placeholder '...' values."
    )

    def _ensure_five_comps(self, output: str, address: str) -> str:
        """If the comps table has fewer than 5 entries, fire a follow-up call
        to fill the missing rows.  Returns the (possibly fixed) report text."""
        found = self._count_comp_rows(output)
        if found >= 5:
            return output

        import logging
        logging.getLogger(__name__).warning(
            "CompsTool: only %d comp row(s) detected for %s — requesting completion",
            found, address,
        )

        fix_user = (
            f"Property address: {address}\n\n"
            f"The following comparable sales report contains only {found} of the "
            f"required 5 comparable sales rows. "
            f"Please add {5 - found} more rows to complete the table, "
            f"using your knowledge of the local market. "
            f"Return the full updated report.\n\n"
            f"Current report:\n{output}"
        )
        try:
            fixed = self._call_llm(self._FIX_SYSTEM, fix_user)
            if self._count_comp_rows(fixed) >= found:   # accept if no worse
                return fixed
        except Exception:
            pass
        return output   # return original if the fix call fails

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
            output = self._ensure_five_comps(output, address)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Rental ─────────────────────────────────────────────────────────────────────

RENTAL_SYSTEM_PROMPT = """You are a rental income and cash flow analysis specialist.
Provide detailed rental analysis using conservative assumptions.

Real government data may be included under "## 🏛️ Live Real Data". When present:
- Use the HUD Fair Market Rents (FMR) as your primary basis for rental income estimates.
  These are official government benchmarks published annually.
- Use the Census income and renter-rate data to contextualise demand.
- Note the source as "HUD Fair Market Rents / US Census" in the footer.

When no real data is provided, use your training knowledge and note "AI estimate".

## Rental & Cash Flow Analysis — {address}

### Rental Income Estimate
| Scenario | Monthly Rent | Annual Rent |
|----------|-------------|-------------|
| Conservative | $X,XXX | $XX,XXX |
| Moderate | $X,XXX | $XX,XXX |
| Optimistic | $X,XXX | $XX,XXX |

### Monthly Cash Flow (Moderate Scenario, 25% down, 30yr fixed)
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
**Grade:** [A+ through F]

*Source: [HUD Fair Market Rents / US Census | AI estimate]. Verify before making investment decisions.*"""


class RentalTool(BaseRealEstateTool):
    skill_name = "rental"
    system_prompt = RENTAL_SYSTEM_PROMPT

    def _fetch_real_data(self, address: str) -> str:
        """Fetch HUD Fair Market Rents and Census income data."""
        sections: list[str] = []

        # HUD Fair Market Rents
        try:
            from data_sources.hud import get_fair_market_rents
            fmr = get_fair_market_rents(address)
            if fmr:
                lines = [
                    f"### HUD Fair Market Rents (FY{fmr.get('year', 2024)}) — ZIP {fmr['zip']}",
                    f"**County / Metro:** {fmr.get('county', 'N/A')} / {fmr.get('metro_area', 'N/A')}",
                ]
                if fmr.get("fmr_studio") is not None:
                    lines.append(f"- Studio (0BR): **${fmr['fmr_studio']:,}/mo**")
                if fmr.get("fmr_1br") is not None:
                    lines.append(f"- 1 Bedroom: **${fmr['fmr_1br']:,}/mo**")
                if fmr.get("fmr_2br") is not None:
                    lines.append(f"- 2 Bedrooms: **${fmr['fmr_2br']:,}/mo**")
                if fmr.get("fmr_3br") is not None:
                    lines.append(f"- 3 Bedrooms: **${fmr['fmr_3br']:,}/mo**")
                if fmr.get("fmr_4br") is not None:
                    lines.append(f"- 4 Bedrooms: **${fmr['fmr_4br']:,}/mo**")
                lines.append(f"- *Source: {fmr['source']}*")
                sections.append("\n".join(lines))
        except Exception:
            pass

        # Census income + renter share
        try:
            from data_sources.census import get_acs_data
            acs = get_acs_data(address)
            if acs:
                lines = [f"### US Census ACS Data — ZIP {acs['zip']}"]
                if acs.get("median_income"):
                    lines.append(
                        f"- Median household income: **${acs['median_income']:,}/yr**"
                        f" (${acs['median_income'] // 12:,}/mo)"
                    )
                own = acs.get("owner_occupied") or 0
                rent = acs.get("renter_occupied") or 0
                if own + rent > 0:
                    pct = int(rent / (own + rent) * 100)
                    lines.append(f"- Renter-occupied housing units: **{pct}%**")
                if acs.get("median_home_value"):
                    lines.append(f"- Median home value: **${acs['median_home_value']:,}**")
                lines.append(f"- *Source: {acs['source']}*")
                sections.append("\n".join(lines))
        except Exception:
            pass

        if not sections:
            return ""

        return (
            "## 🏛️ Live Real Data\n\n"
            "Use the HUD Fair Market Rents below as your primary rental income basis. "
            "These are official US government benchmarks, not estimates.\n\n"
            + "\n\n".join(sections)
        )

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        user_msg = f"Property address: {address}"
        if kwargs.get("purchase_price"):
            user_msg += f"\nSale price: ${kwargs['purchase_price']:,}"
        if kwargs.get("hoa_fees"):
            user_msg += f"\nMonthly HOA fees: ${kwargs['hoa_fees']:,}/mo (use this exact figure in the cash flow table)"

        real_data = self._fetch_real_data(address)
        if real_data:
            user_msg += f"\n\n{real_data}"

        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Mortgage ───────────────────────────────────────────────────────────────────

MORTGAGE_SYSTEM_PROMPT = """You are a mortgage calculator and affordability specialist.

Real mortgage rate data may be included under "## 🏛️ Live Real Data". When present:
- Use the exact FRED/Freddie Mac rates for your calculations.
- Do NOT use the approximate placeholder rates (~7.0%, ~6.3%) — use the real figures.
- Note the source as "Freddie Mac via FRED" in the footer.

When no real data is provided, use current market rates and note "AI estimate".

## Mortgage Analysis — {address}

### Loan Scenarios
Assume estimated purchase price from comps. Show 4 down payment scenarios (5%, 10%, 20%, 25%).

| Down Payment | Loan Amount | Monthly P&I | Total Interest | Monthly PITI |
|-------------|-------------|-------------|----------------|--------------|
| 5% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |
| 10% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |
| 20% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |
| 25% | $XXX,XXX | $X,XXX | $XXX,XXX | $X,XXX |

### Current Rate Used
**30-Year Fixed:** X.XX%
**15-Year Fixed:** X.XX%
*Source: [Freddie Mac via FRED | AI estimate]*

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

    def _fetch_real_data(self, address: str) -> str:
        """Fetch FRED mortgage rates and Census median home value."""
        sections: list[str] = []

        # FRED mortgage rates
        try:
            from data_sources.fred import get_mortgage_rates
            rates = get_mortgage_rates()
            if rates:
                lines = [
                    f"### Current Mortgage Rates ({rates['source']})",
                    f"- **30-year fixed rate: {rates['rate_30yr']:.2f}%**",
                ]
                if rates.get("rate_15yr") is not None:
                    lines.append(f"- **15-year fixed rate: {rates['rate_15yr']:.2f}%**")
                lines.append(f"- As of: {rates['as_of']}")
                sections.append("\n".join(lines))
        except Exception:
            pass

        # Census median home value (useful anchor when no purchase price given)
        try:
            from data_sources.census import get_acs_data
            acs = get_acs_data(address)
            if acs and acs.get("median_home_value"):
                lines = [
                    f"### US Census Median Home Value — ZIP {acs['zip']}",
                    f"- Median owner-occupied home value: **${acs['median_home_value']:,}**",
                ]
                if acs.get("median_income"):
                    lines.append(f"- Median household income: **${acs['median_income']:,}/yr**")
                lines.append(f"- *Source: {acs['source']}*")
                sections.append("\n".join(lines))
        except Exception:
            pass

        if not sections:
            return ""

        return (
            "## 🏛️ Live Real Data\n\n"
            "Use the mortgage rates below for all calculations — "
            "these are real figures from Freddie Mac's weekly survey.\n\n"
            + "\n\n".join(sections)
        )

    def run(self, address: str, **kwargs) -> dict:
        purchase_price = kwargs.get("purchase_price")
        hoa_fees = kwargs.get("hoa_fees")
        prompt = self.system_prompt.replace("{address}", address)
        user_msg = f"Property address: {address}"
        if purchase_price:
            user_msg += f"\nEstimated purchase price: ${purchase_price:,}"
        if hoa_fees:
            user_msg += f"\nMonthly HOA fees: ${hoa_fees:,}/mo (include in PITI calculations)"

        real_data = self._fetch_real_data(address)
        if real_data:
            user_msg += f"\n\n{real_data}"

        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))
