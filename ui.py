"""
ui.py — Streamlit layout, session state management, and graph execution.

Run with: streamlit run main.py
"""
from __future__ import annotations
import os
import logging
from typing import Optional

import streamlit as st

import config
from config import ALL_SKILLS, PARALLEL_SKILLS, SKILL_LABELS
from utils import geocode_address

logger = logging.getLogger(__name__)


def _set_env_if_truthy(var: str, value: str) -> None:
    """Set an env var only when the value is non-empty (never overwrite with '')."""
    if value and value.strip():
        os.environ[var] = value.strip()


# ── Page config ────────────────────────────────────────────────────────────────

def configure_page() -> None:
    st.set_page_config(
        page_title="🏡 Real Estate Agent",
        page_icon="🏡",
        layout="wide",
        initial_sidebar_state="expanded",
    )


_LIGHT_CSS = """
<style>
[data-testid="stSidebar"] { background-color: #f0f4f8; }
.stProgress > div > div { background-color: #2d6a9f !important; }
div[data-testid="metric-container"] {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px;
    border: 1px solid #e0e0e0;
}
.quick-link-btn { margin: 2px 0; }
</style>
"""

_DARK_CSS = """
<style>
/* ── Main surfaces ───────────────────────────────── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="block-container"] {
    background-color: #0e1117 !important;
    color: #e8eaed !important;
}
[data-testid="stHeader"] {
    background-color: #0e1117 !important;
}

/* ── Sidebar ─────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #1a1d27 !important;
    border-right: 1px solid #2d3142;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {
    color: #e8eaed !important;
}

/* ── Metric cards ────────────────────────────────── */
div[data-testid="metric-container"] {
    background: #1e2130 !important;
    border-radius: 8px;
    padding: 12px;
    border: 1px solid #2d3142 !important;
}
div[data-testid="metric-container"] * {
    color: #e8eaed !important;
}

/* ── Inputs ──────────────────────────────────────── */
.stTextInput input,
.stNumberInput input,
textarea {
    background-color: #1e2130 !important;
    color: #e8eaed !important;
    border-color: #2d3142 !important;
}
.stTextInput label,
.stNumberInput label {
    color: #e8eaed !important;
}

/* ── Tabs ────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #1a1d27 !important;
}
.stTabs [data-baseweb="tab"] {
    color: #9aa0ac !important;
}
.stTabs [aria-selected="true"] {
    color: #e8eaed !important;
    border-bottom-color: #4a9eff !important;
}

/* ── Expanders ───────────────────────────────────── */
[data-testid="stExpander"] {
    background-color: #1e2130 !important;
    border-color: #2d3142 !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p {
    color: #e8eaed !important;
}

/* ── Buttons ─────────────────────────────────────── */
.stButton > button {
    background-color: #1e2130 !important;
    border-color: #2d3142 !important;
    color: #e8eaed !important;
}
.stButton > button[kind="primary"] {
    background-color: #1a3c5e !important;
    border-color: #2d6a9f !important;
    color: #ffffff !important;
}

/* ── Checkboxes / toggle ─────────────────────────── */
.stCheckbox label,
.stToggle label {
    color: #e8eaed !important;
}

/* ── Markdown & general text ─────────────────────── */
.stMarkdown, .stMarkdown p,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
.stMarkdown li, .stMarkdown td, .stMarkdown th {
    color: #e8eaed !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: #9aa0ac !important;
}

/* ── Dividers ────────────────────────────────────── */
hr { border-color: #2d3142 !important; }

/* ── Info / warning / error boxes ───────────────── */
[data-testid="stAlert"] {
    background-color: #1e2130 !important;
}

/* ── Progress bar ────────────────────────────────── */
.stProgress > div > div { background-color: #4a9eff !important; }

/* ── Chat messages ───────────────────────────────── */
[data-testid="stChatMessage"] {
    background-color: #1e2130 !important;
    border-color: #2d3142 !important;
}

/* ── Download / link buttons ─────────────────────── */
.stDownloadButton > button,
.stLinkButton > a {
    background-color: #1e2130 !important;
    border-color: #2d3142 !important;
    color: #e8eaed !important;
}

.quick-link-btn { margin: 2px 0; }
</style>
"""


def apply_theme() -> None:
    """Inject light or dark CSS based on session state. Call after init_session()."""
    dark = st.session_state.get("dark_mode", False)
    st.markdown(_DARK_CSS if dark else _LIGHT_CSS, unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────

def init_session() -> None:
    """Initialize session state with defaults (idempotent)."""
    defaults: dict = {
        "report_markdown": None,
        "pdf_path": None,
        "tool_results": {},
        "errors": {},
        "progress_log": [],
        "running": False,
        "address": "",
        "openai_key": config.OPENAI_API_KEY,
        "tavily_key": config.TAVILY_API_KEY,
        "selected_skills": list(ALL_SKILLS),
        "purchase_price": 0,
        "hoa_fees": 0,
        # Widget-key defaults — must be initialised here so the widgets have a
        # single source of truth (session state only, no value= conflict).
        "input_address": "",
        "input_purchase_price": 0,
        "input_hoa_fees": 0,
        # Map state — reset whenever a new address is analyzed.
        # None = not attempted; False = attempted but failed; (lat,lon) = success
        "map_coords": None,
        "map_address": "",
        # Chat with Report
        "chat_messages": [],     # list of {"role": "user"|"assistant", "content": str}
        # Report history — list of recent reports loaded from DB
        "history_loaded": False,
        # Theme
        "dark_mode": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """Render sidebar with API keys, address input, skill toggles, generate button."""
    # ── Apply pending history load BEFORE any widget is instantiated ───────────
    # Streamlit forbids setting a widget's session-state key after that widget
    # has been rendered in the current run.  The load button fires at the bottom
    # of the sidebar (after input_address is already on screen), so we stage the
    # data in pending_load, rerun, and apply it here at the very top of the next
    # run before any widgets exist.
    if "pending_load" in st.session_state:
        load = st.session_state.pending_load
        st.session_state.address               = load["address"]
        st.session_state.input_address         = load["address"]
        pp  = load.get("purchase_price") or 0
        hoa = load.get("hoa_fees") or 0
        st.session_state.purchase_price        = pp
        st.session_state.input_purchase_price  = pp
        st.session_state.hoa_fees              = hoa
        st.session_state.input_hoa_fees        = hoa
        st.session_state.report_markdown       = load.get("report_markdown")
        st.session_state.tool_results          = load.get("tool_results", {})
        st.session_state.errors                = {}
        st.session_state.chat_messages         = []
        st.session_state.map_coords            = None
        st.session_state.map_address           = ""
        del st.session_state["pending_load"]

    with st.sidebar:
        st.title("🏡 Real Estate Agent")
        st.caption("Powered by LangGraph + OpenAI")
        st.divider()

        # API Keys
        openai_key = st.text_input(
            "OpenAI API Key *",
            value=st.session_state.openai_key,
            type="password",
            placeholder="sk-...",
            help="Required. Your key is used only during this session.",
            key="input_openai_key",
        )
        st.session_state.openai_key = openai_key

        tavily_key = st.text_input(
            "Tavily API Key *(optional)*",
            value=st.session_state.tavily_key,
            type="password",
            placeholder="tvly-...",
            help="Enables live web search for more accurate data.",
            key="input_tavily_key",
        )
        st.session_state.tavily_key = tavily_key

        # ── Free real data API keys ────────────────────────────────────────────
        with st.expander("🏛️ Free Real Data APIs", expanded=False):
            st.caption(
                "Connect free government and public APIs for real (non-AI) data. "
                "Each is optional — tools fall back to AI estimates if not set."
            )
            fred_key = st.text_input(
                "FRED API Key",
                value=st.session_state.get("fred_key", config.FRED_API_KEY),
                type="password",
                placeholder="abcdef1234...",
                help="Real mortgage rates (Freddie Mac). "
                     "Free: fred.stlouisfed.org/docs/api/api_key.html",
                key="input_fred_key",
            )
            st.session_state["fred_key"] = fred_key

            census_key = st.text_input(
                "Census API Key",
                value=st.session_state.get("census_key", config.CENSUS_API_KEY),
                type="password",
                placeholder="(optional — works without key)",
                help="Median home values & income. "
                     "Free: api.census.gov/data/key_signup.html",
                key="input_census_key",
            )
            st.session_state["census_key"] = census_key

            hud_key = st.text_input(
                "HUD API Token",
                value=st.session_state.get("hud_key", config.HUD_API_KEY),
                type="password",
                placeholder="eyJ...",
                help="Fair Market Rents by ZIP code. "
                     "Free: huduser.gov/hudapi/public/register.php",
                key="input_hud_key",
            )
            st.session_state["hud_key"] = hud_key

            walkscore_key = st.text_input(
                "Walk Score API Key",
                value=st.session_state.get("walkscore_key", config.WALKSCORE_API_KEY),
                type="password",
                placeholder="(your Walk Score key)",
                help="Walkability / Transit / Bike scores. "
                     "Free: walkscore.com/professional/api.php",
                key="input_walkscore_key",
            )
            st.session_state["walkscore_key"] = walkscore_key

            fema_status = "✅ Active (no key needed)" if True else ""
            st.caption(f"🌊 **FEMA Flood Zones** — {fema_status}")

        # Cache status + clear button
        if config.LLM_CACHE_ENABLED:
            try:
                from langchain_core.globals import get_llm_cache
                llm_cache = get_llm_cache()
                if llm_cache is not None:
                    n_llm = llm_cache.size()
                    n_search = llm_cache.search_size() if hasattr(llm_cache, "search_size") else 0
                    col_cache, col_clear = st.columns([2, 1])
                    parts = [f"{n_llm} LLM"]
                    if n_search:
                        parts.append(f"{n_search} search")
                    col_cache.caption(f"💾 Cache: {', '.join(parts)}")
                    if col_clear.button("Clear", key="btn_clear_cache", width='stretch'):
                        llm_cache.clear()
                        st.toast("Cache cleared (LLM + search)", icon="🗑️")
                        st.rerun()
            except Exception:
                pass

        st.divider()

        # Address — no value= param; session state key is the single source of truth
        st.text_input(
            "🏠 Property Address",
            placeholder="123 Main St, Austin, TX 78701",
            help="Enter a full US property address including city and state.",
            key="input_address",
        )
        address = st.session_state.input_address
        st.session_state.address = address

        # Optional property details
        st.caption("*(Optional)* Known property details improve accuracy:")
        col_price, col_hoa = st.columns(2)
        with col_price:
            st.number_input(
                "Sale Price ($)",
                min_value=0,
                max_value=100_000_000,
                step=1000,
                help="Enter the listed or agreed sale price. Leave 0 to let AI estimate.",
                key="input_purchase_price",
                format="%d",
            )
            st.session_state.purchase_price = st.session_state.input_purchase_price
        with col_hoa:
            st.number_input(
                "HOA Fees ($/mo)",
                min_value=0,
                max_value=10_000,
                step=25,
                help="Monthly HOA fees. Leave 0 if none or unknown.",
                key="input_hoa_fees",
                format="%d",
            )
            st.session_state.hoa_fees = st.session_state.input_hoa_fees

        st.divider()

        # Skill selector
        st.subheader("📋 Analysis Modules")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("All", width='stretch', key="btn_all"):
                st.session_state.selected_skills = list(ALL_SKILLS)
                st.rerun()
        with col2:
            if st.button("Core Only", width='stretch', key="btn_core"):
                st.session_state.selected_skills = [
                    "quick", "screen", "comps", "rental", "neighborhood"
                ]
                st.rerun()

        st.caption("quick & screen always run (validation)")
        selected = []
        for skill in ALL_SKILLS:
            label = SKILL_LABELS.get(skill, skill)
            # quick and screen are always included — show as disabled checkboxes
            if skill in ("quick", "screen"):
                st.checkbox(label, value=True, disabled=True, key=f"ck_{skill}")
                selected.append(skill)
            else:
                checked = skill in st.session_state.selected_skills
                if st.checkbox(label, value=checked, key=f"ck_{skill}"):
                    selected.append(skill)

        # Always keep quick + screen
        if "quick" not in selected:
            selected.insert(0, "quick")
        if "screen" not in selected:
            selected.insert(1, "screen")
        st.session_state.selected_skills = selected

        st.divider()

        # Generate button
        can_generate = bool(address.strip()) and bool(openai_key.strip())
        generate_clicked = st.button(
            "🚀 Generate Report",
            width='stretch',
            disabled=not can_generate or st.session_state.running,
            type="primary",
            key="btn_generate",
        )

        if not can_generate:
            if not address.strip():
                st.caption("⬆️ Enter a property address")
            if not openai_key.strip():
                st.caption("⬆️ Enter your OpenAI API key")

        if generate_clicked and can_generate:
            st.session_state.running = True
            st.session_state.report_markdown = None
            st.session_state.pdf_path = None
            st.session_state.tool_results = {}
            st.session_state.errors = {}
            st.session_state.progress_log = []
            st.session_state.chat_messages = []   # reset chat for new address
            # Reset map so it re-geocodes for the new address
            st.session_state.map_coords = None
            st.session_state.map_address = ""
            st.rerun()

        st.divider()

        # ── Report History ─────────────────────────────────────────────────────
        _render_history_sidebar()

        st.divider()

        # ── Theme toggle ───────────────────────────────────────────────────────
        dark = st.toggle(
            "🌙 Dark Mode",
            value=st.session_state.dark_mode,
            key="toggle_dark_mode",
        )
        if dark != st.session_state.dark_mode:
            st.session_state.dark_mode = dark
            st.rerun()


def _render_history_sidebar() -> None:
    """Show recent analyses in the sidebar with load/delete buttons."""
    try:
        from history import list_reports, load_report, delete_report, clear_history
    except ImportError:
        return

    with st.expander("📚 Report History", expanded=False):
        try:
            reports = list_reports(limit=10)
        except Exception:
            st.caption("History unavailable.")
            return

        if not reports:
            st.caption("No saved reports yet.")
            return

        for r in reports:
            ts_short = r["timestamp"][:16]   # "YYYY-MM-DD HH:MM"
            addr_short = r["address"][:35] + ("…" if len(r["address"]) > 35 else "")
            avg_score = ""
            if r["scores"]:
                vals = list(r["scores"].values())
                avg = int(sum(vals) / len(vals))
                avg_score = f" · {avg}/100"

            col_load, col_del = st.columns([4, 1])
            with col_load:
                if st.button(
                    f"📄 {addr_short}\n{ts_short}{avg_score}",
                    key=f"hist_load_{r['id']}",
                    width='stretch',
                ):
                    full = load_report(r["id"])
                    if full:
                        # Stage data in pending_load — widget keys (input_address
                        # etc.) cannot be set after their widgets are rendered in
                        # the same run.  render_sidebar() drains this at the top
                        # of the NEXT run before any widget is instantiated.
                        st.session_state.pending_load = {
                            "address":        full["address"],
                            "purchase_price": full.get("purchase_price") or 0,
                            "hoa_fees":       full.get("hoa_fees") or 0,
                            "report_markdown": full["report_markdown"],
                            "tool_results":   full["tool_results"],
                        }
                        st.rerun()
            with col_del:
                if st.button("🗑", key=f"hist_del_{r['id']}", help="Delete this report"):
                    delete_report(r["id"])
                    st.rerun()

        if st.button("Clear All History", key="hist_clear", width='stretch'):
            clear_history()
            st.rerun()


# ── Graph execution ────────────────────────────────────────────────────────────

def run_analysis() -> None:
    """Execute the LangGraph workflow and stream progress to the UI."""
    address = st.session_state.address
    openai_key = st.session_state.openai_key
    selected_skills = st.session_state.selected_skills
    tavily_key = st.session_state.tavily_key
    purchase_price = st.session_state.purchase_price or None   # 0 → None (not provided)
    hoa_fees = st.session_state.hoa_fees or None               # 0 → None (not provided)

    # Set API keys at runtime (avoid global state pollution)
    os.environ["OPENAI_API_KEY"] = openai_key
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key

    # Free real data source keys (all optional)
    _set_env_if_truthy("FRED_API_KEY",       st.session_state.get("fred_key", ""))
    _set_env_if_truthy("CENSUS_API_KEY",     st.session_state.get("census_key", ""))
    _set_env_if_truthy("HUD_API_KEY",        st.session_state.get("hud_key", ""))
    _set_env_if_truthy("WALKSCORE_API_KEY",  st.session_state.get("walkscore_key", ""))

    # Lazy import — avoids LLM init at module load time
    from graph import build_graph
    from state import RealEstateState

    initial_state: RealEstateState = {
        "address": address,
        "selected_skills": selected_skills,
        "parsed_data": {},
        "tool_results": {},
        "errors": {},
        "purchase_price": purchase_price,
        "hoa_fees": hoa_fees,
        "validation_passed": False,
        "final_report": "",
        "pdf_path": None,
        "progress": [],
    }

    n_steps = max(len(selected_skills) + 4, 1)
    step = 0

    st.subheader(f"📍 {address}")

    with st.status("🔄 Running analysis...", expanded=True) as status_ctx:
        progress_bar = st.progress(0, text="Starting...")
        try:
            g = build_graph()
            for event in g.stream(initial_state, stream_mode="values"):
                # Collect progress messages
                new_msgs = event.get("progress", [])
                for msg in new_msgs:
                    if msg not in st.session_state.progress_log:
                        st.session_state.progress_log.append(msg)
                        st.write(msg)

                # Advance progress bar
                step = min(step + 1, n_steps)
                pct = int(step / n_steps * 100)
                progress_bar.progress(pct, text=f"{pct}% — analyzing...")

                # Persist partial results for display
                if event.get("tool_results"):
                    st.session_state.tool_results = dict(event["tool_results"])
                if event.get("errors"):
                    st.session_state.errors = dict(event["errors"])
                if event.get("final_report"):
                    st.session_state.report_markdown = event["final_report"]
                if event.get("pdf_path"):
                    st.session_state.pdf_path = event["pdf_path"]

            progress_bar.progress(100, text="✅ Complete!")
            status_ctx.update(label="✅ Analysis complete!", state="complete")

            # ── Save to history ────────────────────────────────────────────────
            _save_to_history(address)

        except Exception as e:
            progress_bar.empty()
            status_ctx.update(label="❌ Analysis failed", state="error")
            st.error(f"**Error:** {e}")
            logger.exception("Graph execution error for address: %s", address)

    st.session_state.running = False


def _save_to_history(address: str) -> None:
    """Persist completed analysis to SQLite history."""
    try:
        from history import save_report
        report_md = st.session_state.get("report_markdown") or ""
        tool_results = st.session_state.get("tool_results") or {}
        if report_md and tool_results:
            save_report(
                address,
                report_md,
                tool_results,
                purchase_price=st.session_state.get("purchase_price") or 0,
                hoa_fees=st.session_state.get("hoa_fees") or 0,
            )
    except Exception:
        logger.debug("History save failed (non-fatal)", exc_info=True)


# ── Location map ───────────────────────────────────────────────────────────────

def render_map(address: str) -> None:
    """Display an interactive OpenStreetMap tile centred on the property address."""
    import pandas as pd

    cached_coords = st.session_state.get("map_coords")   # None / False / (lat,lon)
    cached_addr   = st.session_state.get("map_address", "")

    if cached_addr != address or cached_coords is None:
        with st.spinner("📍 Locating property on map…"):
            result = geocode_address(address)
        st.session_state.map_coords  = result if result is not None else False
        st.session_state.map_address = address
        cached_coords = st.session_state.map_coords

    with st.expander("🗺️ Location Map", expanded=True):
        if not cached_coords:
            st.info(
                "Map unavailable — the address could not be located. "
                "This can happen with brand-new developments or very rural "
                "properties not yet in OpenStreetMap. "
                "The analysis above is unaffected."
            )
            return

        lat, lon = cached_coords
        df = pd.DataFrame({"lat": [lat], "lon": [lon]})
        st.map(df, zoom=14, width='stretch')
        st.caption(
            f"📍 **{address}** &nbsp;·&nbsp; "
            f"{lat:.5f}°, {lon:.5f}° &nbsp;·&nbsp; "
            "Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors"
        )


# ── Property Quick Links ───────────────────────────────────────────────────────

def _strip_unit(address: str) -> str:
    """Remove unit designators from an address string.

    '747 Seneca St #C40, Ventura, CA' → '747 Seneca St, Ventura, CA'

    Used for sites whose search/routing breaks on unit numbers (#, Apt, Unit, Ste).
    """
    import re
    return re.sub(
        r"\s+(?:#\S+|[Aa]pt\.?\s*\S+|[Uu]nit\s+\S+|[Ss]te\.?\s*\S+|[Ss]uite\s+\S+)",
        "",
        address,
    ).strip()


def render_quick_links(address: str) -> None:
    """Render external property link buttons (Zillow, Redfin, Trulia, Google Maps)."""
    from urllib.parse import quote, quote_plus

    enc          = quote(address, safe="")          # %20 — path segments & Maps
    enc_plus     = quote_plus(_strip_unit(address)) # + encoding, unit stripped — Redfin hash
    enc_no_unit  = quote(_strip_unit(address), safe="")  # %20, unit stripped — Trulia path

    # Zillow: path-based search with %20 encoding
    zillow_url  = f"https://www.zillow.com/homes/{enc}/"

    # Redfin: hash-fragment routing (#location=).
    # React SPA reads window.location.hash via URLSearchParams, which decodes
    # '+' as space — quote_plus is correct here. Unit stripped because a bare '#'
    # inside the hash value terminates the fragment and truncates the address.
    redfin_url  = f"https://www.redfin.com/search#location={enc_plus}"

    # Trulia (owned by Zillow): path-based search, same reliable pattern as Zillow.
    # Realtor.com replaced because their slug router is brittle and returns 503
    # for addresses it can't match — Trulia handles %20-encoded addresses cleanly.
    # Unit stripped for cleaner search results.
    trulia_url  = f"https://www.trulia.com/homes/{enc_no_unit}/"

    maps_url    = f"https://www.google.com/maps/search/{enc}"

    with st.expander("🔗 Property Quick Links", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.link_button("🏠 Zillow",       zillow_url,  width='stretch')
        c2.link_button("🔴 Redfin",       redfin_url,  width='stretch')
        c3.link_button("🟠 Trulia",        trulia_url,  width='stretch')
        c4.link_button("🗺️ Google Maps",  maps_url,    width='stretch')


# ── Street View ────────────────────────────────────────────────────────────────

def render_street_view(address: str) -> None:
    """Embed a Google Street View iframe for the property."""
    from urllib.parse import quote_plus
    enc = quote_plus(address)
    # Google Maps embed (no API key required for the basic embed)
    embed_url = (
        "https://www.google.com/maps/embed/v1/streetview"
        f"?key=AIzaSyD-9tSrke72PouQMnMX-a7eZSW0jkFMBWY"  # public demo key
        f"&location={enc}&heading=210&pitch=10&fov=75"
    )
    # Fallback: use the standard maps search embed (works without API key)
    fallback_url = (
        f"https://maps.google.com/maps?q={enc}"
        "&output=embed&z=16&layer=c&cbll=0,0&cbp=12,0,,0,0"
    )

    with st.expander("🏘️ Street View", expanded=False):
        st.markdown(
            f"""<iframe
                width="100%" height="300"
                src="https://www.google.com/maps/embed/v1/place?key=AIzaSyD-9tSrke72PouQMnMX-a7eZSW0jkFMBWY&q={enc}&zoom=16"
                style="border:0; border-radius:8px;"
                allowfullscreen="" loading="lazy"
                referrerpolicy="no-referrer-when-downgrade">
            </iframe>""",
            unsafe_allow_html=True,
        )
        st.caption(
            "Map data © Google. Street View availability varies by location. "
            "[Open in Google Maps]"
            f"(https://www.google.com/maps/search/{enc})"
        )


# ── Charts ─────────────────────────────────────────────────────────────────────

def render_charts(tool_results: dict, address: str) -> None:
    """Render the Score Dashboard and Financial Charts tabs."""
    try:
        import plotly.graph_objects as go
        import charts as ch
    except ImportError:
        st.info("Install plotly (`pip install plotly`) to enable interactive charts.")
        return

    tab_radar, tab_cashflow, tab_comps = st.tabs(
        ["🎯 Score Dashboard", "💵 Cash Flow", "📊 Comp Prices"]
    )

    with tab_radar:
        fig = ch.score_radar(tool_results, address)
        if fig:
            st.plotly_chart(fig, width='stretch')
            # Score table
            import re
            scores = {}
            for skill, md in tool_results.items():
                m = re.search(r"(?:score[:\s]+)?(\d{1,3})\s*/?\s*100", md, re.I)
                if m:
                    v = int(m.group(1))
                    if 0 <= v <= 100:
                        scores[skill] = v
            if scores:
                avg = int(sum(scores.values()) / len(scores))
                cols = st.columns(min(len(scores), 5))
                items = sorted(scores.items(), key=lambda x: -x[1])
                for i, (skill, score) in enumerate(items):
                    grade = (
                        "A+" if score >= 85 else
                        "A"  if score >= 70 else
                        "B"  if score >= 55 else
                        "C"  if score >= 40 else
                        "D"  if score >= 25 else "F"
                    )
                    label = SKILL_LABELS.get(skill, skill).lstrip("⚡📋📊🏠🏘️💰📈🏢🔨💼🔍⚖️📝🏖️🧾 ")
                    cols[i % len(cols)].metric(label, f"{score}/100", grade)
                st.metric("🏆 Average Score", f"{avg}/100")
        else:
            st.info("No scored results yet. Generate a report to see the dashboard.")

    with tab_cashflow:
        fig = ch.cashflow_waterfall(tool_results)
        if fig:
            st.plotly_chart(fig, width='stretch')
            st.caption(
                "Cash flow breakdown parsed from the Rental & Cash Flow analysis. "
                "Negative bars are expenses; the final bar is net monthly cash flow."
            )
        else:
            st.info("Run the Rental & Cash Flow analysis to see this chart.")

    with tab_comps:
        fig = ch.comp_prices_bar(tool_results)
        if fig:
            st.plotly_chart(fig, width='stretch')
            st.caption(
                "Comparable sale prices parsed from the Comparable Sales analysis."
            )
        else:
            st.info("Run the Comparable Sales analysis to see this chart.")


# ── Chat with Report ───────────────────────────────────────────────────────────

def render_chat(report_md: str, openai_key: str) -> None:
    """Let users ask questions about the generated report via GPT."""
    with st.expander("💬 Chat with Report", expanded=False):
        if not report_md:
            st.info("Generate a report first, then ask questions about it here.")
            return

        if not openai_key.strip():
            st.info("Enter your OpenAI API key in the sidebar to use chat.")
            return

        # Display existing chat history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        user_input = st.chat_input("Ask a question about this property…")
        if user_input:
            st.session_state.chat_messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    reply = _chat_with_report(report_md, user_input, openai_key)
                st.markdown(reply)
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})


def _chat_with_report(report_md: str, question: str, openai_key: str) -> str:
    """Call OpenAI to answer a question grounded in the report."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        # Truncate report to stay within context limits
        MAX_REPORT_CHARS = 12_000
        truncated = report_md[:MAX_REPORT_CHARS]
        if len(report_md) > MAX_REPORT_CHARS:
            truncated += "\n\n*[report truncated for chat context]*"

        system = (
            "You are a real estate expert assistant. "
            "The user has generated an AI property analysis report and wants to ask questions about it. "
            "Answer concisely and accurately, citing specific numbers from the report when available. "
            "If the answer is not in the report, say so honestly rather than guessing."
        )
        user_msg = f"""## Property Report\n\n{truncated}\n\n---\n\n## Question\n{question}"""

        os.environ["OPENAI_API_KEY"] = openai_key
        llm = ChatOpenAI(model=config.OPENAI_MODEL, temperature=0.2, max_tokens=600)
        response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user_msg)])
        return response.content
    except Exception as e:
        logger.warning("Chat LLM call failed: %s", e)
        return f"⚠️ Could not get a response: {e}"


# ── Results display ────────────────────────────────────────────────────────────

def render_results() -> None:
    """Render analysis results: metrics, charts, map, quick links, street view, tabs, chat."""
    tool_results: dict = st.session_state.tool_results
    errors: dict = st.session_state.errors
    report_md: Optional[str] = st.session_state.report_markdown
    pdf_path: Optional[str] = st.session_state.pdf_path
    address: str = st.session_state.address

    if not tool_results and not report_md:
        # Welcome state
        st.markdown("""
        ## Welcome to 🏡 Real Estate Agent

        Enter a property address in the sidebar and click **Generate Report** to get:

        | Module | What It Provides |
        |--------|-----------------|
        | ⚡ Quick Snapshot | 60-second property assessment |
        | 📊 Comparable Sales | Comps, price/sqft, value range |
        | 🏠 Rental & Cash Flow | Cap rate, NOI, cash-on-cash return |
        | 💰 Mortgage Calculator | Loan scenarios, affordability |
        | 🏘️ Neighborhood Analysis | Schools, safety, walkability |
        | 📈 Market Conditions | Trends, inventory, forecast |
        | 💼 Investment Strategies | Buy & Hold, BRRRR, Flip analysis |
        | 🔨 Fix & Flip Analysis | Rehab budget, 70% rule |
        | 🏢 Commercial Analysis | NOI, cap rate, lease terms |
        | ⚖️ Property Comparison | Subject vs 2 alternatives |
        | 📝 MLS Listing | 4 buyer-profile descriptions |
        | 🏖️ STR / Airbnb | Nightly rates, regulations, STR vs LTR |
        | 🧾 Property Tax | County rates, exemptions, appeal analysis |
        | 🔍 Full Property Analysis | Composite score & 90-day action plan |

        *Powered by OpenAI GPT-4o-mini. For educational purposes only — not financial advice.*
        """)
        return

    # ── Metrics row ────────────────────────────────────────────────────────────
    n_success = len(tool_results)
    n_error = len(errors)
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Analyses Complete", n_success)
    c2.metric("⚠️ Errors", n_error)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            c3.download_button(
                label="📥 Download PDF",
                data=f.read(),
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                width='stretch',
            )
    elif report_md:
        c3.download_button(
            label="📋 Download Markdown",
            data=report_md.encode("utf-8"),
            file_name="real_estate_report.md",
            mime="text/markdown",
            width='stretch',
        )

    # ── Interactive Charts ──────────────────────────────────────────────────────
    if tool_results:
        render_charts(tool_results, address)

    st.divider()

    # ── Location map ───────────────────────────────────────────────────────────
    if address:
        render_map(address)

    # ── Property quick links ───────────────────────────────────────────────────
    if address:
        render_quick_links(address)

    # ── Street View ───────────────────────────────────────────────────────────
    if address:
        render_street_view(address)

    st.divider()

    # ── Build tab list: Full Report first, then individual skills, then Errors ──
    tab_labels = ["📄 Full Report"]
    for skill in tool_results:
        tab_labels.append(SKILL_LABELS.get(skill, skill))
    if errors:
        tab_labels.append("⚠️ Errors")

    tabs = st.tabs(tab_labels)

    # Full report tab
    with tabs[0]:
        if report_md:
            st.markdown(report_md)
        else:
            st.info("Full report not yet generated.")

    # Individual skill tabs
    for i, skill in enumerate(tool_results, start=1):
        with tabs[i]:
            st.markdown(tool_results[skill])

    # Error tab
    if errors:
        with tabs[-1]:
            for skill, msg in errors.items():
                label = SKILL_LABELS.get(skill, skill)
                st.error(f"**{label}**: {msg}")

    # ── Chat with Report ───────────────────────────────────────────────────────
    if report_md:
        st.divider()
        render_chat(report_md, st.session_state.openai_key)


# ── Progress log ───────────────────────────────────────────────────────────────

def render_progress_log() -> None:
    """Show execution log in a collapsed expander."""
    log = st.session_state.get("progress_log", [])
    if log:
        with st.expander("📋 Execution Log", expanded=False):
            for msg in log:
                st.text(msg)


# ── App entrypoint ─────────────────────────────────────────────────────────────

def main() -> None:
    """Main Streamlit app entry point."""
    configure_page()
    init_session()
    apply_theme()

    # Header
    st.title("🏡 Real Estate Agent")
    st.caption("Comprehensive AI-powered property analysis • Powered by LangGraph + OpenAI")

    # Sidebar renders input controls and triggers st.session_state.running
    render_sidebar()

    # Execute graph if triggered
    if st.session_state.running:
        run_analysis()
        st.rerun()  # Re-render so the button reflects running=False and results display

    # Show results (or welcome screen)
    render_results()

    # Progress log at bottom
    render_progress_log()
