"""
tools/additional_tools.py — Short-Term Rental (STR) and Property Tax tools.
"""
from __future__ import annotations
from tools.base import BaseRealEstateTool

# ── STR / Airbnb ───────────────────────────────────────────────────────────────

STR_SYSTEM_PROMPT = """You are a short-term rental (Airbnb/VRBO) investment specialist.

Live web-search data may be included under "## 🌐 Live STR Data". When present:
- Extract real nightly rates, occupancy figures, and regulation notes.
- Note the source as "Live web data (Tavily)" in the footer.

When no live data is provided, use your training knowledge and note "AI estimate".

Produce the analysis in this exact markdown format:

## Short-Term Rental Analysis — {address}

### STR Revenue Estimate
| Scenario | Nightly Rate | Occupancy | Monthly Revenue | Annual Revenue |
|----------|-------------|-----------|----------------|----------------|
| Conservative | $XXX | 55% | $X,XXX | $XX,XXX |
| Moderate | $XXX | 70% | $X,XXX | $XX,XXX |
| Optimistic | $XXX | 85% | $X,XXX | $XX,XXX |

### Monthly Cash Flow — STR vs Long-Term Rental (Moderate Scenario)
| Item | STR | LTR |
|------|-----|-----|
| Gross Revenue | $X,XXX | $X,XXX |
| Platform / Vacancy | -$XXX | -$XXX |
| Mortgage (P&I) | -$X,XXX | -$X,XXX |
| Property Tax | -$XXX | -$XXX |
| Insurance (STR premium) | -$XXX | -$XXX |
| Utilities | -$XXX | $0 |
| Supplies & Amenities | -$XXX | $0 |
| Cleaning (per stay) | -$XXX | $0 |
| Property Mgmt (20% STR / 10% LTR) | -$XXX | -$XXX |
| **Net Cash Flow** | **$XXX** | **$XXX** |

### Local STR Regulations
**Permit Required:** [Yes / No / Unknown]
**Annual Permit Cost:** $XXX
**Owner-Occupancy Required:** [Yes / No]
**Night Cap:** [X nights/year or None]
**Key Restrictions:** [summary]
**Compliance Risk:** [Low / Moderate / High]

### Key STR Metrics
| Metric | Value | Benchmark |
|--------|-------|-----------|
| Revenue per Available Night (RevPAN) | $XXX | $100–$200 good |
| Annual Gross Revenue (Moderate) | $XX,XXX | — |
| Gross STR Yield | X.X% | ≥8% = good |
| STR Premium over LTR | +XX% | — |
| Break-Even Occupancy | XX% | <50% = strong |

### Score Breakdown
- Revenue Potential: XX/25
- Cash Flow vs LTR: XX/25
- Regulation Friendliness: XX/25
- Market Demand: XX/25

**Score:** XX/100
**Grade:** [A+ through F]
**Verdict:** [STRONG STR / GOOD STR / MARGINAL / BETTER AS LTR]

*Source: [Live web data (Tavily) | AI estimate]. Verify local regulations before listing.*"""

_STR_DOMAINS = [
    "airdna.co", "alltherooms.com", "rabbu.com",
    "mashvisor.com", "airbnb.com", "vrbo.com",
]
_MAX_STR_CONTEXT = 5_000


class STRTool(BaseRealEstateTool):
    skill_name = "str"
    system_prompt = STR_SYSTEM_PROMPT

    def _fetch_str_data(self, address: str) -> str:
        """Gather live STR nightly rates and local regulation data via Tavily."""
        sections: list[str] = []

        # 1. Nightly rates and occupancy from STR data portals
        rates = self._web_search(
            f'Airbnb VRBO short-term rental nightly rate occupancy "{address}" 2024 2025',
            max_results=4,
            include_domains=_STR_DOMAINS,
        )
        if rates:
            sections.append(f"### STR Market Data (Airbnb / AirDNA)\n{rates}")

        # 2. Local STR regulations
        # Extract city/state from address for a tighter regulation search
        parts = [p.strip() for p in address.split(",")]
        city_state = ", ".join(parts[1:3]) if len(parts) >= 3 else address
        regs = self._web_search(
            f"short-term rental regulations permit {city_state} Airbnb VRBO 2024 2025",
            max_results=3,
        )
        if regs:
            sections.append(f"### Local STR Regulations\n{regs}")

        if not sections:
            return ""

        body = "\n\n".join(sections)
        if len(body) > _MAX_STR_CONTEXT:
            body = body[:_MAX_STR_CONTEXT] + "\n\n*[data truncated for length]*"

        return (
            "## 🌐 Live STR Data\n\n"
            "Use the figures below for nightly rates, occupancy, and regulations.\n\n"
            + body
        )

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        user_msg = f"Property address: {address}"
        if kwargs.get("purchase_price"):
            user_msg += f"\nPurchase price: ${kwargs['purchase_price']:,}"
        if kwargs.get("hoa_fees"):
            user_msg += f"\nMonthly HOA: ${kwargs['hoa_fees']:,}/mo"

        live_data = self._fetch_str_data(address)
        if live_data:
            user_msg += f"\n\n{live_data}"

        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Property Tax ───────────────────────────────────────────────────────────────

TAX_SYSTEM_PROMPT = """You are a property tax analyst specialising in US residential real estate.

Live web-search data may be included under "## 🌐 Live Tax Data". When present:
- Extract actual county tax rates, assessment ratios, and exemption amounts.
- Note the source as "Live web data (Tavily)" in the footer.

When no live data is provided, use your training knowledge and note "AI estimate".

Produce the analysis in this exact markdown format:

## Property Tax Analysis — {address}

### Current Tax Estimate
**County / Jurisdiction:** [county name, state]
**Estimated Market Value:** $XXX,XXX
**Assessment Ratio:** XX% of market value
**Assessed Value:** $XXX,XXX
**Effective Tax Rate:** X.XX%
**Annual Property Tax:** $X,XXX
**Monthly Escrow:** $XXX

### Tax Breakdown by Jurisdiction
| Jurisdiction | Millage Rate | Annual Amount |
|-------------|-------------|---------------|
| County | XX.XX mills | $X,XXX |
| City / Municipal | XX.XX mills | $XXX |
| School District | XX.XX mills | $X,XXX |
| Special Districts | XX.XX mills | $XXX |
| **Total** | **XX.XX mills** | **$X,XXX** |

### Available Exemptions
| Exemption | Reduction | Eligible? |
|-----------|-----------|-----------|
| Homestead (owner-occupied) | $XX,XXX off assessed | Yes (if primary residence) |
| Senior (65+) | $XX,XXX or X% | Check eligibility |
| Veteran / Disabled | $XX,XXX | Check eligibility |
| **Effective Annual Tax (with Homestead)** | | **$X,XXX** |

### Tax Trend (5 Years)
**Assessment Trend:** [Increasing X.X%/yr / Stable / Decreasing]
**Rate Trend:** [Increasing / Stable / Decreasing]
**Projected Tax in 5 Years:** $X,XXX/yr

### Appeal Analysis
**Is Property Over-Assessed?** [Likely / Possibly / Unlikely]
**Estimated Fair Value vs Assessed Value:** $X,XXX [over/under]
**Appeal Recommended:** [Yes / No] — [brief reason]
**Typical Appeal Savings:** $XXX–$X,XXX/year

### Score Breakdown
- Tax Rate Competitiveness: XX/25
- Exemption Availability: XX/25
- Assessment Accuracy: XX/25
- Trend / Stability: XX/25

**Score:** XX/100
**Grade:** [A+ through F]

*Source: [Live web data (Tavily) | AI estimate]. Verify with county assessor before closing.*"""

_TAX_DOMAINS = [
    "smartasset.com", "taxfoundation.org", "ownwell.com",
    "propertytax101.org", "zillow.com", "realtor.com",
]
_MAX_TAX_CONTEXT = 5_000


class PropertyTaxTool(BaseRealEstateTool):
    skill_name = "tax"
    system_prompt = TAX_SYSTEM_PROMPT

    def _fetch_tax_data(self, address: str) -> str:
        """Gather live property tax rates and county assessor data via Tavily."""
        sections: list[str] = []

        parts = [p.strip() for p in address.split(",")]
        county_query = ", ".join(parts[1:]) if len(parts) >= 2 else address

        # 1. County property tax rates from authoritative sources
        rates = self._web_search(
            f"property tax rate {county_query} county millage assessment ratio 2024 2025",
            max_results=4,
            include_domains=_TAX_DOMAINS,
        )
        if rates:
            sections.append(f"### County Tax Rates\n{rates}")

        # 2. Homestead and other exemptions
        exemptions = self._web_search(
            f"homestead exemption property tax {county_query} 2024 2025",
            max_results=3,
        )
        if exemptions:
            sections.append(f"### Tax Exemptions\n{exemptions}")

        if not sections:
            return ""

        body = "\n\n".join(sections)
        if len(body) > _MAX_TAX_CONTEXT:
            body = body[:_MAX_TAX_CONTEXT] + "\n\n*[data truncated for length]*"

        return (
            "## 🌐 Live Tax Data\n\n"
            "Use the figures below for tax rates, assessment ratios, and exemptions.\n\n"
            + body
        )

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        user_msg = f"Property address: {address}"
        if kwargs.get("purchase_price"):
            user_msg += f"\nEstimated purchase / market value: ${kwargs['purchase_price']:,}"

        live_data = self._fetch_tax_data(address)
        if live_data:
            user_msg += f"\n\n{live_data}"

        try:
            output = self._call_llm(prompt, user_msg)
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))
