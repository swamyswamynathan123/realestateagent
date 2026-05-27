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

# Run all tests (no API key required — all LLM calls are mocked)
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
               commercial, flip, invest, analyze, compare, listing)
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

All 13 analysis tools live in `tools/` and share the same contract:

- Subclass `BaseRealEstateTool` (`tools/base.py`)
- Set class attributes `skill_name` and `system_prompt`
- Implement `run(address, **kwargs) -> dict` — call `_call_llm()`, return `_success_result()` or `_error_result()`
- `_call_llm()` wraps `_call_llm_with_retry()` (tenacity, 3 attempts) and unwraps `RetryError` so callers see the original exception

`tools/__init__.py` holds `TOOL_REGISTRY` (dict of skill name → class) and `get_tool(skill_name)` (instantiates on demand). The graph only calls `get_tool()`; it never imports tool classes directly.

### Adding a new skill

1. Add a subclass of `BaseRealEstateTool` to the appropriate module in `tools/`
2. Register it in `TOOL_REGISTRY` in `tools/__init__.py`
3. Add the name to `PARALLEL_SKILLS` and `SKILL_LABELS` in `config.py`

The graph and UI pick it up automatically — no changes needed there.

### Skill registry vs. config

`config.py` owns the canonical skill list (`ALL_SKILLS`, `PARALLEL_SKILLS`, `SKILL_LABELS`). `tools/__init__.py` owns instantiation. The two must stay in sync: every name in `ALL_SKILLS` must have an entry in `TOOL_REGISTRY`.

### Streamlit session state

`ui.py:init_session()` sets defaults once (idempotent). All persistent UI data lives in `st.session_state` (not module globals). The graph is executed inside `run_analysis()` by iterating `g.stream(initial_state, stream_mode="values")`; each yielded event is a full state snapshot. The graph singleton is built lazily by `graph.get_graph()` and reused across re-runs.

`quick` and `screen` checkboxes are always forced on (disabled in the UI). The user can deselect any of the 11 parallel skills; `selected_skills` in session state reflects the live selection.

### PDF generation

`utils.generate_pdf_report()` converts the assembled markdown report to PDF using ReportLab. PDFs are written to `reports/` (configurable via `PDF_OUTPUT_DIR`). The markdown parser is line-by-line and handles H1/H2/H3, bullet lists, inline bold (`**text**`), and horizontal rules — it does not handle tables beyond rendering them as body text.

### LLM calls

All tools use `langchain_openai.ChatOpenAI`. The model and API key are read from `config.py` at tool instantiation time. The API key is injected into `os.environ` at the start of `run_analysis()` in `ui.py` so that a key entered in the sidebar takes effect without restarting the process.

### Tests

Tests use `pytest-mock`. The `mock_llm` fixture in `conftest.py` returns a `MagicMock` whose `.invoke()` returns a canned markdown string containing `Score: 75/100`. No real API calls are made. `test_graph.py` patches `graph.get_tool` directly so the graph topology is exercised without any LLM calls.
