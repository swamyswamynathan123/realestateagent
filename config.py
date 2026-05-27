"""
config.py — environment variables and LLM settings.
Load this before importing any tool or graph module.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "2048"))
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))

# ── Tavily (optional web search) ──────────────────────────────────────────────
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
USE_WEB_SEARCH: bool = bool(TAVILY_API_KEY)

# ── PDF ───────────────────────────────────────────────────────────────────────
PDF_OUTPUT_DIR: str = os.getenv("PDF_OUTPUT_DIR", "reports")

# ── Skills registry ───────────────────────────────────────────────────────────
# Parallel skills — run after validation (quick + screen)
PARALLEL_SKILLS: list[str] = [
    "comps", "rental", "neighborhood", "mortgage",
    "market", "commercial", "flip", "invest",
    "analyze", "compare", "listing",
]

# All skills in execution order
ALL_SKILLS: list[str] = ["quick", "screen"] + PARALLEL_SKILLS

# Skill display names for UI
SKILL_LABELS: dict[str, str] = {
    "quick":        "Quick Snapshot",
    "screen":       "Property Screen",
    "comps":        "Comparable Sales",
    "rental":       "Rental & Cash Flow",
    "neighborhood": "Neighborhood Analysis",
    "mortgage":     "Mortgage Calculator",
    "market":       "Market Conditions",
    "commercial":   "Commercial Analysis",
    "flip":         "Fix & Flip Analysis",
    "invest":       "Investment Strategies",
    "analyze":      "Full Property Analysis",
    "compare":      "Property Comparison",
    "listing":      "MLS Listing Description",
}
