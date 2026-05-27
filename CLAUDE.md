# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

A virtual environment is at `.venv/`. Activate it first:

```powershell
# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (cmd)
.\.venv\Scripts\activate.bat
```

```powershell
# Run the app
streamlit run main.py

# Run all tests (no API key required — all LLM and HTTP calls are mocked)
pytest tests/ -v

# Run a single test file
pytest tests/test_graph.py -v

# Run a single test
pytest tests/test_graph.py::test_graph_compiles -v

# Verify a module imports cleanly
python -c "from graph import build_graph; g = build_graph(); print(g.nodes)"

# Run directly inside venv without activating
.\.venv\Scripts\pytest tests/ -v
.\.venv\Scripts\streamlit run main.py
```

No build step. No linter configured.

## Architecture

The app is a Streamlit frontend that drives a LangGraph `StateGraph`. The state flows through nodes in `graph.py`; each node calls a tool from `tools/`; the results are merged into `RealEstateState` and finally rendered by `ui.py`.

### Execution order

```
parse_address → run_quick → run_screen
                                │
                   valid?  ─────┤
                     yes        │ no → generate_report (early exit)
                                │
              Send() fan-out to all selected parallel skills
              (comps, rental, neighborhood, mortgage, market,
               commercial, flip, invest, analyze, compare, listing,
               str, tax)
                                │
              aggregate_results → generate_report → generate_pdf → END
```

`quick` and `screen` always run first (sequential). `screen` sets `validation_passed`; the `route_after_screen` conditional edge either short-circuits to `generate_report` or fans out via `Send` to every skill in `selected_skills` that is in `PARALLEL_SKILLS`.

### State

`RealEstateState` (TypedDict in `state.py`) carries all data through the graph. Two fields use annotated reducers because parallel nodes write to them concurrently:

- `tool_results: Annotated[dict, merge_dicts]` — skill name → markdown string
- `errors: Annotated[dict, merge_dicts]` — skill name → error message
- `progress: Annotated[list, append_list]` — streamed to the UI

`_current_skill` is injected dynamically into the state dict by `route_after_screen` when constructing each `Send` object; it is not declared in the TypedDict.

### Tools

All 15 analysis tools live in `tools/` and share the same contract:

- Subclass `BaseRealEstateTool` (`tools/base.py`)
- Set class attributes `skill_name` and `system_prompt`
- Implement `run(address, **kwargs) -> dict` — call `_call_llm()`, return `_success_result()` or `_error_result()`
- `_call_llm()` wraps `_call_llm_with_retry()` (tenacity, 3 attempts) and unwraps `RetryError` so callers see the original exception

`tools/__init__.py` holds `TOOL_REGISTRY` (dict of skill name → class) and `get_tool(skill_name)` (instantiates on demand). The graph only calls `get_tool()`; it never imports tool classes directly.

### Real data injection pattern

Tools that have a corresponding free data source implement `_fetch_real_data(address) -> str`:

1. Call the relevant `data_sources/` functions (e.g., `get_mortgage_rates()`, `get_fair_market_rents()`)
2. Format the returned dicts into a `## 🏛️ Live Real Data\n\n...` markdown block
3. Prepend the block to the user message passed to `_call_llm()`
4. The system prompt instructs the LLM to use the real figures when that header is present

The three tools that use real data injection:
- **RentalTool** — HUD Fair Market Rents + Census ACS
- **MortgageTool** — FRED mortgage rates + Census ACS
- **NeighborhoodTool** — Walk Score (walkability/transit/bike) + FEMA flood zone + Census demographics

### Adding a new skill

1. Add a subclass of `BaseRealEstateTool` to the appropriate module in `tools/`
2. Register it in `TOOL_REGISTRY` in `tools/__init__.py`
3. Add the name to `PARALLEL_SKILLS` and `SKILL_LABELS` in `config.py`

The graph and UI pick it up automatically — no changes needed there.

### Skill registry vs. config

`config.py` owns the canonical skill list (`ALL_SKILLS`, `PARALLEL_SKILLS`, `SKILL_LABELS`). `tools/__init__.py` owns instantiation. The two must stay in sync: every name in `ALL_SKILLS` must have an entry in `TOOL_REGISTRY`. The `test_tool_registry_has_all_skills` test enforces this.

### Data sources

`data_sources/` is a standalone package of free public API clients. Each module:

- Has a single top-level fetch function (e.g., `get_mortgage_rates(api_key=None) -> dict | None`)
- Returns `None` on any error (network, parse, missing key) — callers must handle `None`
- Caches responses in SQLite via `data_sources/_cache.py` with per-source TTLs (8–720 hours)

**Cache isolation trap:** `_cache.get/put` use `db: Optional[str] = None` with `_db = db if db is not None else _CACHE_DB` resolved at call time — not `db=_CACHE_DB` at definition time. This matters for test isolation: tests pass a `tmp_path` db path to bypass production cache.

`utils.geocode_address()` is decorated with `@functools.lru_cache(maxsize=200)` so tools can call it freely without re-hitting the network within the same process.

### charts.py

Three Plotly chart helpers, each returning `None` if the required data is absent:

- `score_radar(tool_results, address)` — Scatterpolar radar of all skill scores (parsed via `_extract_score`)
- `cashflow_waterfall(tool_results)` — Waterfall chart parsed from the rental markdown table rows
- `comp_prices_bar(tool_results)` — Horizontal bar chart parsed from the comps markdown table

### history.py

SQLite-backed report history (`report_history.db`). Key functions:

- `save_report(address, report_markdown, tool_results, scores)` — inserts a row, auto-generating a timestamp
- `list_reports(limit=20)` — returns summary rows (id, address, timestamp, score count)
- `load_report(id)` — returns the full row including tool_results (JSON-deserialized)
- `delete_report(id)` / `clear_history()` — cleanup

### Streamlit session state

`ui.py:init_session()` sets defaults once (idempotent). All persistent UI data lives in `st.session_state` (not module globals). The graph is executed inside `run_analysis()` by iterating `g.stream(initial_state, stream_mode="values")`; each yielded event is a full state snapshot. The graph singleton is built lazily by `graph.get_graph()` and reused across re-runs.

`quick` and `screen` checkboxes are always forced on (disabled in the UI). The user can deselect any of the 13 parallel skills; `selected_skills` in session state reflects the live selection.

Key session state keys added beyond the original set:
- `chat_messages` — list of `{role, content}` dicts for the chat panel
- `fred_key`, `census_key`, `hud_key`, `walkscore_key` — optional API keys entered in the "Free Real Data APIs" sidebar expander

`_set_env_if_truthy(var, value)` is a module-level helper in `ui.py` that sets `os.environ[var] = value` only when `value` is non-empty, preventing blank strings from overriding real env vars.

### PDF generation

`utils.generate_pdf_report()` converts the assembled markdown report to PDF using ReportLab. PDFs are written to `reports/` (configurable via `PDF_OUTPUT_DIR`). The markdown parser is line-by-line and handles H1/H2/H3, bullet lists, inline bold (`**text**`), and horizontal rules — it does not handle tables beyond rendering them as body text.

### LLM calls

All tools use `langchain_openai.ChatOpenAI`. The model and API key are read from `config.py` at tool instantiation time. The API key (and optional data source keys) are injected into `os.environ` via `_set_env_if_truthy()` at the start of `run_analysis()` in `ui.py` so that keys entered in the sidebar take effect without restarting the process.

### Tests

Tests use `pytest-mock`. The `mock_llm` fixture in `conftest.py` returns a `MagicMock` whose `.invoke()` returns a canned markdown string containing `Score: 75/100`. No real API calls are made. `test_graph.py` patches `graph.get_tool` directly so the graph topology is exercised without any LLM calls.

`tests/test_data_sources.py` (24 tests) covers all five data source modules plus the SQLite cache. It uses `unittest.mock.patch` to stub `urllib.request.urlopen` / `requests.get` and passes unique `tmp_path`-based SQLite paths to avoid cross-test cache contamination.

Current test count: **91 passing**.
