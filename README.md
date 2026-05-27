# 🏡 Real Estate Agent

A Streamlit web application powered by a **LangGraph** orchestration workflow that accepts a property address and generates a comprehensive, multi-dimensional real estate report — complete with interactive charts, report history, AI chat, and PDF export.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-red?logo=streamlit)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-purple?logo=openai)
![Tests](https://img.shields.io/badge/Tests-91%20passing-brightgreen)

---

## ✨ Features

- **15 specialized analysis modules** — comparables, rental income, mortgage, neighborhood, market, investment strategies, fix-and-flip, commercial, STR/Airbnb, property tax, and more
- **Free real data sources** — live mortgage rates (FRED/Freddie Mac), rental benchmarks (HUD FMR), walkability scores (Walk Score), flood zone data (FEMA NFHL), and Census demographics injected into AI prompts
- **Parallel execution** — LangGraph fans out to all modules simultaneously, then aggregates results
- **Address validation** — property screen runs first; invalid addresses short-circuit early
- **Interactive charts** — Plotly radar (score dashboard), waterfall (cash flow breakdown), bar (comp prices)
- **Report history** — SQLite-backed history browser; reload any past report instantly
- **Chat with your report** — ask follow-up questions about any analysis section via GPT
- **Property quick links** — one-click links to Zillow, Redfin, Realtor.com, and Google Maps
- **Street view embed** — Google Maps Street View inline in the app
- **Location map** — geocoded property pin rendered via Folium
- **PDF export** — professional ReportLab-generated PDF downloadable from the browser
- **Real-time progress** — streaming graph events update the status bar as each module completes
- **Graceful error handling** — individual module failures are captured and reported; the rest of the analysis continues

---

## 📋 Analysis Modules

| Module | What it produces |
|--------|-----------------|
| ⚡ **Quick Snapshot** | 60-second BUY / HOLD / AVOID signal with score |
| 📋 **Property Screen** | Address validation + 5-criteria investment screen |
| 📊 **Comparable Sales** | 5 comps with price/sq ft, adjusted value range |
| 🏠 **Rental & Cash Flow** | Cap rate, NOI, DSCR, 3-scenario cash flow table (with real HUD FMR rents) |
| 💰 **Mortgage Calculator** | 4 down-payment scenarios, affordability thresholds (with real FRED rates) |
| 🏘️ **Neighborhood Analysis** | Schools, safety, walkability, amenities, growth (with real Walk Score + FEMA flood zone) |
| 📈 **Market Conditions** | Seller's/buyer's market, price trends, 12-month forecast |
| 💼 **Investment Strategies** | Buy & Hold vs BRRRR vs Fix & Flip comparison |
| 🔨 **Fix & Flip Analysis** | Rehab budget breakdown, 70% rule check, ROI |
| 🏢 **Commercial Analysis** | NOI, cap rate, DSCR, lease type, tenant quality |
| ⚖️ **Property Comparison** | Subject property vs 2 comparable alternatives |
| 📝 **MLS Listing** | 4 buyer-profile listing descriptions + headline options |
| 🔍 **Full Property Analysis** | Weighted composite score (0–100) + 90-day action plan |
| 🏖️ **STR / Airbnb Analysis** | Short-term rental revenue, occupancy, platform strategy |
| 🧾 **Property Tax** | Tax assessment, exemptions, effective rate, appeal potential |

---

## 🏛️ Free Real Data Sources

Five real data sources augment the AI analysis with live government and public API data. All are free; most require a one-time key registration.

| Source | What it provides | Key required? |
|--------|-----------------|---------------|
| **FRED** (Freddie Mac via St. Louis Fed) | Current 30yr / 15yr fixed mortgage rates | Yes — [free](https://fred.stlouisfed.org/docs/api/api_key.html) |
| **HUD Fair Market Rents** | Official government rental benchmarks by ZIP (0BR–4BR) | Yes — [free](https://www.huduser.gov/hudapi/public/register.php) |
| **Walk Score API** | Walkability, transit, and bike scores (5,000 req/day free) | Yes — [free](https://www.walkscore.com/professional/api.php) |
| **FEMA NFHL** | Flood zone classification (AE, X, VE, etc.) + SFHA flag | **No key needed** |
| **US Census ACS** | Median home value, household income, population by ZIP | Optional — [free](https://api.census.gov/data/key_signup.html) |

Real data is fetched on every analysis run, cached in SQLite with per-source TTLs (8–720 hours), and injected into the LLM prompt under a `## 🏛️ Live Real Data` header so the model uses real figures rather than estimates.

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 2. Install dependencies

```powershell
cd c:\claude\projects\realestateagent
pip install -r requirements.txt
```

### 3. Configure environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your API key:

```bash
OPENAI_API_KEY=sk-...

# Optional — enables live web search for more accurate STR/Market data
TAVILY_API_KEY=tvly-...

# Optional — enables real data injection (highly recommended)
FRED_API_KEY=...
HUD_API_KEY=...
WALKSCORE_API_KEY=...
CENSUS_API_KEY=...
```

### 4. Launch

```powershell
streamlit run main.py
```

App opens at **http://localhost:8501**

---

## 🖥️ UI Walkthrough

```
┌─────────────────────────────────┬──────────────────────────────────────────────────┐
│  Sidebar                        │  Main Area                                       │
│  ───────────────────────────    │  ──────────────────────────────────────────────  │
│  🔑 OpenAI API Key              │  ✅ Analyses Complete  ⚠️ Errors  📥 PDF         │
│  🔑 Tavily API Key (opt.)       │                                                  │
│  🏛️ Free Real Data APIs ▼       │  [📊 Score Dashboard] [💧 Cash Flow] [🏠 Comps] │
│    FRED / HUD / WalkScore /     │   ← interactive Plotly charts →                 │
│    Census keys                  │                                                  │
│  🏠 Property Address            │  📍 Map  🔗 Quick Links  🌐 Street View          │
│                                 │                                                  │
│  📋 Analysis Modules            │  [Full Report] [Quick] [Comps] [Rental] ...      │
│   ☑ All / Core Only             │   ← tabs, one per completed module →            │
│   ☑ Quick Snapshot (forced)     │                                                  │
│   ☑ Property Screen (forced)    │  # 🏡 Real Estate Report                        │
│   ☑ Comparable Sales            │  ## 123 Main St, Austin TX                      │
│   ☑ Rental & Cash Flow          │                                                  │
│   ☑ Mortgage Calculator         │  **Property Score:** 78/100  Grade: A            │
│   ☑ Neighborhood Analysis       │  **Signal:** BUY                                 │
│   ☑ Market Conditions           │  ...                                             │
│   ☑ Investment Strategies       │                                                  │
│   ☑ Fix & Flip Analysis         │  💬 Chat with this report ▼                     │
│   ☑ Commercial Analysis         │  Ask: "What's the estimated cap rate?"           │
│   ☑ Property Comparison         │                                                  │
│   ☑ MLS Listing                 │  📋 Execution Log ▼                             │
│   ☑ Full Analysis               │  📍 Parsing address...                           │
│   ☑ STR / Airbnb Analysis       │  ✅ quick complete                               │
│   ☑ Property Tax                │  ✅ screen complete                              │
│                                 │  ✅ comps complete                               │
│  [🚀 Generate Report]           │  ...                                             │
│                                 │                                                  │
│  📁 Report History ▼            │                                                  │
│   123 Main St — May 27          │                                                  │
│   456 Oak Ave — May 26          │                                                  │
└─────────────────────────────────┴──────────────────────────────────────────────────┘
```

---

## 🧠 How the LangGraph Workflow Works

```
START
  │
  ▼
parse_address ──► run_quick ──► run_screen
                                    │
                      ┌─────────────┴──────────────────┐
                 valid?│yes                        no   │
                       │                               ▼
                       │                      generate_report
                       │                      (validation error)
                       │
               Send() parallel fan-out:
               ┌──────┬──────┬─────────┬─────────┬─────┬─────┐
               ▼      ▼      ▼         ▼         ▼     ▼     ▼
             comps  rental  neighbor  mortgage  market str  tax ...
               │      │      │         │         │     │    │
               └──────┴──────┴────┬────┴─────────┴─────┴────┘
                                  ▼
                         aggregate_results
                                  │
                                  ▼
                         generate_report
                                  │
                                  ▼
                          generate_pdf
                                  │
                                 END
```

**Key design decisions:**

- `quick` and `screen` always run first (sequential) — screen validates the address
- If screen returns `VALIDATION_FAILED`, the graph short-circuits to the report node immediately
- All other modules run in parallel using LangGraph's `Send` API
- `tool_results` and `errors` dicts use annotated reducers (`merge_dicts`) so parallel writes are safe
- The singleton `get_graph()` compiles the graph once and reuses it across Streamlit re-runs

---

## 📁 Project Structure

```
realestateagent/
├── main.py                    # Entrypoint: streamlit run main.py
├── config.py                  # Env vars, LLM settings, skill registry
├── state.py                   # RealEstateState TypedDict + ToolResult Pydantic model
├── graph.py                   # LangGraph StateGraph: nodes, edges, routing
├── ui.py                      # Streamlit layout, session state, progress streaming
├── utils.py                   # Report formatter + ReportLab PDF generator
├── charts.py                  # Plotly chart helpers (radar, waterfall, bar)
├── history.py                 # SQLite report history (save/load/list/delete)
├── cache.py                   # LangChain SQLite LLM cache
│
├── data_sources/              # Free real data API clients
│   ├── __init__.py            # Exports all fetch functions
│   ├── _cache.py              # SQLite TTL cache for data source responses
│   ├── fred.py                # FRED mortgage rates (30yr/15yr)
│   ├── census.py              # US Census ACS (home values, income, population)
│   ├── hud.py                 # HUD Fair Market Rents (0BR–4BR by ZIP)
│   ├── walk_score.py          # Walk Score (walkability, transit, bike)
│   └── fema.py                # FEMA NFHL flood zone classification
│
├── tools/
│   ├── __init__.py            # TOOL_REGISTRY dict + get_tool() factory
│   ├── base.py                # BaseRealEstateTool ABC (retry, score parsing)
│   ├── validation.py          # QuickTool, ScreenTool
│   ├── property_analysis.py   # CompsTool, RentalTool (HUD FMR), MortgageTool (FRED)
│   ├── location_tools.py      # NeighborhoodTool (WalkScore+FEMA), MarketTool, ListingTool
│   ├── investment_tools.py    # InvestTool, FlipTool, CommercialTool, AnalyzeTool, CompareTool
│   └── additional_tools.py    # STRTool, PropertyTaxTool
│
├── tests/
│   ├── conftest.py            # Shared fixtures (mock_llm, sample_address)
│   ├── test_config.py         # Config and skill registry tests
│   ├── test_state.py          # Reducer and Pydantic model tests
│   ├── test_tools.py          # All 15 tool wrappers (28 tests)
│   ├── test_utils.py          # PDF generation + report formatting
│   ├── test_graph.py          # LangGraph workflow tests
│   └── test_data_sources.py   # Data source clients + cache isolation (24 tests)
│
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🧪 Running Tests

```powershell
cd c:\claude\projects\realestateagent
pytest tests/ -v
```

Expected: **91 passed**

Tests use `pytest-mock` to stub out OpenAI calls and `responses`/`unittest.mock` to stub HTTP calls — no API key required to run the test suite.

```powershell
# Run a specific module
pytest tests/test_graph.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

---

## ⚙️ Configuration

All settings are read from environment variables (`.env` file or shell):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model to use (`gpt-4o` for higher quality) |
| `OPENAI_MAX_TOKENS` | `2048` | Max tokens per module response |
| `OPENAI_TEMPERATURE` | `0.1` | Lower = more deterministic output |
| `TAVILY_API_KEY` | *(optional)* | Enables live web search via Tavily |
| `FRED_API_KEY` | *(optional)* | FRED mortgage rates (Freddie Mac weekly survey) |
| `CENSUS_API_KEY` | *(optional)* | Census ACS data (works without key at lower rate) |
| `HUD_API_KEY` | *(optional)* | HUD Fair Market Rents by ZIP code |
| `WALKSCORE_API_KEY` | *(optional)* | Walk Score walkability/transit/bike scores |
| `PDF_OUTPUT_DIR` | `reports/` | Where generated PDFs are saved |
| `LLM_CACHE_ENABLED` | `true` | Cache LLM responses (disable with `false`) |
| `LLM_CACHE_DB` | `.langchain_cache.db` | Path to the LLM SQLite cache |

---

## 🔧 Extending the App

### Adding a new analysis module

1. Add your tool class to the appropriate file in `tools/`:

```python
class MyCustomTool(BaseRealEstateTool):
    skill_name = "custom"
    system_prompt = "You are a ... analyst.\n\n## Custom Analysis — {address}\n..."

    def run(self, address: str, **kwargs) -> dict:
        prompt = self.system_prompt.replace("{address}", address)
        try:
            output = self._call_llm(prompt, f"Property address: {address}")
            return self._success_result(address, output)
        except Exception as e:
            return self._error_result(address, str(e))
```

2. Register it in `tools/__init__.py`:

```python
from tools.my_module import MyCustomTool

TOOL_REGISTRY = {
    ...
    "custom": MyCustomTool,
}
```

3. Add it to `config.py`:

```python
PARALLEL_SKILLS = [..., "custom"]
SKILL_LABELS["custom"] = "🔧 Custom Analysis"
```

The graph and UI pick it up automatically — no graph or UI changes needed.

---

### Adding a real data source

Follow the pattern in `data_sources/`:

1. Create `data_sources/my_source.py` — implement a `get_my_data(address, api_key=None) -> dict | None` function that uses `_cache.get/put` for TTL caching
2. Export it from `data_sources/__init__.py`
3. Call it in the relevant tool's `_fetch_real_data(address)` method and inject the result into the LLM prompt under a `## 🏛️ Live Real Data` header

---

### Switching to a different LLM

Replace `langchain_openai.ChatOpenAI` in `tools/base.py` with any LangChain-compatible chat model:

```python
from langchain_anthropic import ChatAnthropic

self.llm = ChatAnthropic(model="claude-opus-4-7", api_key=...)
```

---

## 📊 Scoring System

Each module produces a **0–100 score** parsed from its markdown output:

| Score | Grade | Signal |
|-------|-------|--------|
| 85–100 | **A+** | STRONG BUY |
| 70–84 | **A** | BUY |
| 55–69 | **B** | HOLD / WATCH |
| 40–54 | **C** | CAUTION |
| 25–39 | **D** | PASS |
| 0–24 | **F** | AVOID |

The **Full Property Analysis** module computes a weighted composite:

| Dimension | Weight |
|-----------|--------|
| Value & Comps | 25% |
| Income Potential | 20% |
| Neighborhood Quality | 20% |
| Investment Upside | 20% |
| Market Conditions | 15% |

The **Score Dashboard** chart renders all module scores in a Plotly radar chart for at-a-glance comparison.

---

## ⚠️ Disclaimer

This application uses AI to generate real estate analysis for **educational and research purposes only**. Live data from FRED, HUD, Walk Score, FEMA, and Census is fetched in good faith but may be delayed, incomplete, or inaccurate for a specific property.

**Always consult a licensed real estate professional, attorney, and/or financial advisor before making any investment decisions.**

---

## 📄 License

MIT
