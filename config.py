"""
config.py — environment variables and LLM settings.
Load this before importing any tool or graph module.
"""
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

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

# ── LLM caching ───────────────────────────────────────────────────────────────
# Responses are cached by (prompt, llm_string) key so re-running the same
# address skips the OpenAI API entirely.  Disable with LLM_CACHE_ENABLED=false.
LLM_CACHE_ENABLED: bool = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
LLM_CACHE_DB: str = os.getenv("LLM_CACHE_DB", ".langchain_cache.db")

# ── Skills registry ───────────────────────────────────────────────────────────
# Parallel skills — run after validation (quick + screen)
PARALLEL_SKILLS: list[str] = [
    "comps", "rental", "neighborhood", "mortgage",
    "market", "commercial", "flip", "invest",
    "analyze", "compare", "listing",
    "str", "tax",
]

# All skills in execution order
ALL_SKILLS: list[str] = ["quick", "screen"] + PARALLEL_SKILLS

# Skill display names for UI
SKILL_LABELS: dict[str, str] = {
    "quick":        "⚡ Quick Snapshot",
    "screen":       "📋 Property Screen",
    "comps":        "📊 Comparable Sales",
    "rental":       "🏠 Rental & Cash Flow",
    "neighborhood": "🏘️ Neighborhood Analysis",
    "mortgage":     "💰 Mortgage Calculator",
    "market":       "📈 Market Conditions",
    "commercial":   "🏢 Commercial Analysis",
    "flip":         "🔨 Fix & Flip Analysis",
    "invest":       "💼 Investment Strategies",
    "analyze":      "🔍 Full Property Analysis",
    "compare":      "⚖️ Property Comparison",
    "listing":      "📝 MLS Listing Description",
    "str":          "🏖️ STR / Airbnb Analysis",
    "tax":          "🧾 Property Tax",
}


# ── Cache initialisation ───────────────────────────────────────────────────────

def setup_llm_cache() -> None:
    """Register the SQLite LLM cache with LangChain's global registry.

    Called once at import time.  Tools instantiated later automatically
    inherit the cache — no changes needed in tool code.
    """
    if not LLM_CACHE_ENABLED:
        logger.debug("LLM caching disabled via LLM_CACHE_ENABLED=false")
        return
    try:
        from langchain_core.globals import set_llm_cache
        from cache import SQLiteCache
        set_llm_cache(SQLiteCache(db_path=LLM_CACHE_DB))
        logger.debug("LLM cache active: %s", LLM_CACHE_DB)
    except Exception:
        logger.exception("Failed to initialise LLM cache — proceeding without caching")


setup_llm_cache()
