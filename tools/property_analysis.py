"""
tools/property_analysis.py — Comparable Sales, Rental/Cash Flow, Mortgage Calculator
"""
from __future__ import annotations
from tools.base import BaseRealEstateTool

# ── Comps ──────────────────────────────────────────────────────────────────────

COMPS_SYSTEM_PROMPT = """You are a real estate comparable sales analyst.

## Comparable Sales Analysis — {address}

### Subject Property Estimate
**Estimated Value:** $XXX,XXX
**Price per Sq Ft:** $XXX/sq ft
**Property Type:** [type]

### Comparable Sales (5 comps)
| Address | Sale Price | Sq Ft | $/Sq Ft | Distance | Days Ago | Notes |
|---------|-----------|-------|---------|----------|----------|-------|
| [comp 1]| $XXX,XXX | X,XXX | $XXX | X.X mi | XX | adj |
| [comp 2]| $XXX,XXX | X,XXX | $XXX | X.X mi | XX | adj |
| [comp 3]| $XXX,XXX | X,XXX | $XXX | X.X mi | XX | adj |
| [comp 4]| $XXX,XXX | X,XXX | $XXX | X.X mi | XX | adj |
| [comp 5]| $XXX,XXX | X,XXX | $XXX | X.X mi | XX | adj |

### Adjustment Analysis
**Adjusted Value Range:** $XXX,XXX - $XXX,XXX
**Median Comp Price:** $XXX,XXX

### Comp Quality Assessment
- **Data Quality:** XX/25
- **Price Alignment:** XX/25
- **Comp Relevance:** XX/25
- **Market Trend:** XX/25

**Score:** XX/100
**Grade:** [A+ through F]

*AI estimate based on market knowledge. Verify with MLS data.*"""


class CompsTool(BaseRealEstateTool):
    skill_name = "comps"
    system_prompt = COMPS_SYSTEM_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
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
