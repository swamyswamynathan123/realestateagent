"""
tools/investment_tools.py — Invest, Flip, Commercial, Analyze, Compare
"""
from __future__ import annotations
from tools.base import BaseRealEstateTool

# ── Invest ─────────────────────────────────────────────────────────────────────

INVEST_PROMPT = """You are a real estate investment strategist. Analyze 3 strategies.

## Investment Strategy Analysis — {address}

### Strategy 1: Buy & Hold
**Feasibility Score:** XX/100
- Down Payment Needed: $XX,XXX (20%)
- Monthly Cash Flow: $XXX (conservative)
- 5-Year Appreciation Gain: $XX,XXX (est.)
- Total 5-Year Return: $XX,XXX
- Recommendation: [PURSUE / CONSIDER / SKIP]

### Strategy 2: BRRRR (Buy, Rehab, Rent, Refi, Repeat)
**Feasibility Score:** XX/100
- Estimated Rehab Cost: $XX,XXX
- ARV (After-Repair Value): $XXX,XXX
- Equity Created: $XX,XXX
- Cash-Out Refi Amount: $XXX,XXX
- Remaining Equity: $XX,XXX
- Recommendation: [PURSUE / CONSIDER / SKIP]

### Strategy 3: Fix & Flip
**Feasibility Score:** XX/100
- Purchase Price: $XXX,XXX
- Rehab Budget: $XX,XXX
- ARV: $XXX,XXX
- Expected Profit: $XX,XXX
- ROI: XX.X%
- 70% Rule Check: [PASS / FAIL] (limit = $XXX,XXX)
- Recommendation: [PURSUE / CONSIDER / SKIP]

### Best Strategy Recommendation
**Winner:** [Strategy Name]
**Reasoning:** [2-3 sentences]

**Overall Investment Score:** XX/100
**Grade:** [A+ through F]"""


class InvestTool(BaseRealEstateTool):
    skill_name = "invest"
    system_prompt = INVEST_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Flip ───────────────────────────────────────────────────────────────────────

FLIP_PROMPT = """You are a fix-and-flip specialist. Provide detailed rehab budgeting.

## Fix & Flip Analysis — {address}

### Deal Numbers
| Item | Amount |
|------|--------|
| Purchase Price | $XXX,XXX |
| Rehab Budget | $XX,XXX |
| Holding Costs (6mo) | $X,XXX |
| Selling Costs (8%) | $XX,XXX |
| Total All-In Cost | $XXX,XXX |
| ARV (After-Repair Value) | $XXX,XXX |
| **Projected Profit** | **$XX,XXX** |
| **ROI** | **XX.X%** |

### 70% Rule
- 70% of ARV = $XXX,XXX
- Max Purchase + Rehab = $XXX,XXX
- Current Deal: [PASSES / FAILS] the 70% Rule

### Rehab Budget Breakdown
| Category | Budget | Priority |
|----------|--------|----------|
| Kitchen | $X,XXX | High |
| Bathrooms | $X,XXX | High |
| Flooring | $X,XXX | High |
| Paint | $X,XXX | High |
| Roof | $X,XXX | Med |
| HVAC | $X,XXX | Med |
| Landscaping | $X,XXX | Low |
| Miscellaneous (10%) | $X,XXX | Buffer |
| **Total** | **$XX,XXX** | |

**Score:** XX/100
**Grade:** [A+ through F]
**Recommendation:** [PURSUE / CONSIDER / SKIP]"""


class FlipTool(BaseRealEstateTool):
    skill_name = "flip"
    system_prompt = FLIP_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Commercial ─────────────────────────────────────────────────────────────────

COMMERCIAL_PROMPT = """You are a commercial real estate analyst.

## Commercial Property Analysis — {address}

### Property Overview
**Property Type:** [Office / Retail / Industrial / Mixed-Use / Multi-Family 5+]
**Estimated Size:** X,XXX sq ft
**Year Built:** XXXX
**Zoning:** [code and description]

### Income Analysis (NOI)
| Income Item | Monthly | Annual |
|-------------|---------|--------|
| Gross Rental Income | $X,XXX | $XX,XXX |
| Vacancy (X%) | -$XXX | -$X,XXX |
| Other Income | $XXX | $X,XXX |
| **Effective Gross Income** | $X,XXX | $XX,XXX |
| Operating Expenses | -$X,XXX | -$XX,XXX |
| **Net Operating Income (NOI)** | **$X,XXX** | **$XX,XXX** |

### Valuation Metrics
| Metric | Value | Benchmark |
|--------|-------|-----------|
| Cap Rate | X.X% | Market avg: X.X% |
| Price/Sq Ft | $XXX | Market avg: $XXX |
| GRM | XX | <10 = good |
| DSCR | X.XX | >=1.25 needed |

### Lease Analysis
**Lease Type:** [NNN / Gross / Modified Gross]
**Remaining Term:** X years
**Tenant Quality:** [A / B / C]

**Score:** XX/100
**Grade:** [A+ through F]"""


class CommercialTool(BaseRealEstateTool):
    skill_name = "commercial"
    system_prompt = COMMERCIAL_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Analyze (Full Composite) ───────────────────────────────────────────────────

ANALYZE_PROMPT = """You are a senior real estate analyst. Produce the MASTER composite analysis.

## Full Property Analysis — {address}

### Property Score (0-100)
| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|---------|
| Value & Comps | 25% | XX | XX.X |
| Income Potential | 20% | XX | XX.X |
| Neighborhood Quality | 20% | XX | XX.X |
| Investment Upside | 20% | XX | XX.X |
| Market Conditions | 15% | XX | XX.X |
| **TOTAL** | 100% | | **XX.X** |

### Overall Grade
**Property Score:** XX/100
**Grade:** [A+ / A / B / C / D / F]
**Investment Signal:** [STRONG BUY / BUY / HOLD / PASS / AVOID]

### Executive Summary
[4-5 sentence executive summary covering key strengths, risks, and recommendation]

### Top 5 Strengths
1. ...
2. ...
3. ...
4. ...
5. ...

### Top 5 Risks
1. ...
2. ...
3. ...
4. ...
5. ...

### 90-Day Action Plan
1. [Immediate action if buying]
2. [Due diligence step]
3. [Financing step]
4. [Exit strategy consideration]
5. [Risk mitigation step]

*For educational purposes only. Not financial advice.*"""


class AnalyzeTool(BaseRealEstateTool):
    skill_name = "analyze"
    system_prompt = ANALYZE_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Compare ────────────────────────────────────────────────────────────────────

COMPARE_PROMPT = """You are a property comparison specialist.
Compare the subject property against 2 similar alternatives in the same area.

## Property Comparison — {address}

### Subject vs Alternatives
| Factor | Subject Property | Alternative A | Alternative B |
|--------|-----------------|---------------|---------------|
| Address | {address} | [similar nearby] | [similar nearby] |
| Est. Price | $XXX,XXX | $XXX,XXX | $XXX,XXX |
| Sq Ft | X,XXX | X,XXX | X,XXX |
| Price/Sq Ft | $XXX | $XXX | $XXX |
| Year Built | XXXX | XXXX | XXXX |
| Bedrooms | X | X | X |
| Bathrooms | X | X | X |
| Est. Rent | $X,XXX | $X,XXX | $X,XXX |
| Cap Rate | X.X% | X.X% | X.X% |

### Comparison Score
| | Subject | Alt A | Alt B |
|-|---------|-------|-------|
| Value | XX/100 | XX/100 | XX/100 |
| Income | XX/100 | XX/100 | XX/100 |
| Location | XX/100 | XX/100 | XX/100 |
| **Total** | **XX/100** | **XX/100** | **XX/100** |

### Winner: [Subject / Alternative A / Alternative B]
**Reasoning:** [2-3 sentences explaining the best choice]"""


class CompareTool(BaseRealEstateTool):
    skill_name = "compare"
    system_prompt = COMPARE_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))
