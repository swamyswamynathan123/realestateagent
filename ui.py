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

logger = logging.getLogger(__name__)


# ── Page config ────────────────────────────────────────────────────────────────

def configure_page() -> None:
    st.set_page_config(
        page_title="🏡 Real Estate Agent",
        page_icon="🏡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #f0f4f8; }
    .stProgress > div > div { background-color: #2d6a9f !important; }
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)


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
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """Render sidebar with API keys, address input, skill toggles, generate button."""
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
                    if col_clear.button("Clear", key="btn_clear_cache", use_container_width=True):
                        llm_cache.clear()
                        st.toast("Cache cleared (LLM + search)", icon="🗑️")
                        st.rerun()
            except Exception:
                pass

        st.divider()

        # Address
        address = st.text_input(
            "🏠 Property Address",
            value=st.session_state.address,
            placeholder="123 Main St, Austin, TX 78701",
            help="Enter a full US property address including city and state.",
            key="input_address",
        )
        st.session_state.address = address

        # Optional property details
        st.caption("*(Optional)* Known property details improve accuracy:")
        col_price, col_hoa = st.columns(2)
        with col_price:
            purchase_price = st.number_input(
                "Sale Price ($)",
                min_value=0,
                max_value=100_000_000,
                value=st.session_state.purchase_price,
                step=1000,
                help="Enter the listed or agreed sale price. Leave 0 to let AI estimate.",
                key="input_purchase_price",
                format="%d",
            )
            st.session_state.purchase_price = purchase_price
        with col_hoa:
            hoa_fees = st.number_input(
                "HOA Fees ($/mo)",
                min_value=0,
                max_value=10_000,
                value=st.session_state.hoa_fees,
                step=25,
                help="Monthly HOA fees. Leave 0 if none or unknown.",
                key="input_hoa_fees",
                format="%d",
            )
            st.session_state.hoa_fees = hoa_fees

        st.divider()

        # Skill selector
        st.subheader("📋 Analysis Modules")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("All", use_container_width=True, key="btn_all"):
                st.session_state.selected_skills = list(ALL_SKILLS)
                st.rerun()
        with col2:
            if st.button("Core Only", use_container_width=True, key="btn_core"):
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
            use_container_width=True,
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

        except Exception as e:
            progress_bar.empty()
            status_ctx.update(label="❌ Analysis failed", state="error")
            st.error(f"**Error:** {e}")
            logger.exception("Graph execution error for address: %s", address)

    st.session_state.running = False


# ── Results display ────────────────────────────────────────────────────────────

def render_results() -> None:
    """Render analysis results: metrics, PDF download, and tabbed skill outputs."""
    tool_results: dict = st.session_state.tool_results
    errors: dict = st.session_state.errors
    report_md: Optional[str] = st.session_state.report_markdown
    pdf_path: Optional[str] = st.session_state.pdf_path

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
        | 🔍 Full Property Analysis | Composite score & 90-day action plan |

        *Powered by OpenAI GPT-4o-mini. For educational purposes only — not financial advice.*
        """)
        return

    # Metrics row
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
                use_container_width=True,
            )
    elif report_md:
        c3.download_button(
            label="📋 Download Markdown",
            data=report_md.encode("utf-8"),
            file_name="real_estate_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.divider()

    # Build tab list: Full Report first, then individual skills, then Errors
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
