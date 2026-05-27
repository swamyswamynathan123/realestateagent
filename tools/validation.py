"""
tools/validation.py — Quick snapshot + Property screener

realestate_quick:  60-second property snapshot.
realestate_screen: Validates address, checks basic feasibility.
                   Sets validation_passed flag in result.
"""
from __future__ import annotations
from tools.base import BaseRealEstateTool

# ── Quick ──────────────────────────────────────────────────────────────────────

QUICK_SYSTEM_PROMPT = """You are a real estate expert providing a rapid 60-second property snapshot.
Given a property address, produce a concise markdown report with these sections:

## Quick Snapshot — {address}

**Property Type:** [SFR / Condo / Multi-Family / Commercial / Land]
**Estimated Value:** $XXX,XXX
**Estimated Rent:** $X,XXX/mo

### ⚡ Top 3 Strengths
1. ...
2. ...
3. ...

### ⚠️ Top 3 Concerns
1. ...
2. ...
3. ...

### Quick Score
**Score:** XX/100
**Grade:** [A+ / A / B / C / D / F]
**Signal:** [STRONG BUY / BUY / HOLD / PASS / AVOID]

*Disclaimer: AI estimation for research only. Not financial advice.*

Use your training knowledge of US real estate markets. Be concise.
"""


class QuickTool(BaseRealEstateTool):
    skill_name = "quick"
    system_prompt = QUICK_SYSTEM_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))


# ── Screen ─────────────────────────────────────────────────────────────────────

SCREEN_SYSTEM_PROMPT = """You are a real estate screening agent. Your job is to:
1. Validate that the provided address is a real, parseable US property address.
2. Identify the property type (SFR, condo, multi-family, commercial, land, unknown).
3. Screen it against 5 investment criteria: cash flow potential, appreciation potential,
   BRRRR feasibility, first-time buyer suitability, short-term rental (STR) potential.

Respond in this exact markdown format:

## Property Screen — {address}

**Validation:** VALID | INVALID
**Property Type:** [type]
**City/State:** [city, state]
**Zip Code:** [zip or N/A]

### Investment Criteria Screen
| Criteria | Rating | Notes |
|----------|--------|-------|
| Cash Flow Potential | HIGH/MED/LOW | ... |
| Appreciation Potential | HIGH/MED/LOW | ... |
| BRRRR Feasibility | HIGH/MED/LOW | ... |
| First-Time Buyer Fit | YES/NO | ... |
| STR Potential | HIGH/MED/LOW | ... |

### Screen Summary
[2-3 sentence summary of overall suitability]

**Score:** XX/100
**Grade:** [A+ through F]

If the address is clearly not a real property (gibberish, missing city/state, impossible format),
start your response with exactly: VALIDATION_FAILED: [reason]
"""


class ScreenTool(BaseRealEstateTool):
    skill_name = "screen"
    system_prompt = SCREEN_SYSTEM_PROMPT

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            validation_passed = not output.strip().startswith("VALIDATION_FAILED")
            result = self._success_result(address, output)
            result["validation_passed"] = validation_passed
            return result
        except Exception as e:
            r = self._error_result(address, str(e))
            r["validation_passed"] = False
            return r
