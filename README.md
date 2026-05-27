# 🏡 Real Estate Agent

A Streamlit web application powered by a **LangGraph** orchestration workflow that accepts a property address and generates a comprehensive, multi-dimensional real estate report — complete with PDF export.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-red?logo=streamlit)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-purple?logo=openai)
![Tests](https://img.shields.io/badge/Tests-42%20passing-brightgreen)

---

## ✨ Features

- **13 specialized analysis modules** — comparables, rental income, mortgage, neighborhood, market, investment strategies, fix-and-flip, commercial, and more
- **Parallel execution** — LangGraph fans out to all modules simultaneously, then aggregates results
- **Address validation** — property screen runs first; invalid addresses short-circuit early
- **Unified report** — all module outputs assembled into one scrollable markdown document
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
| 🏠 **Rental & Cash Flow** | Cap rate, NOI, DSCR, 3-scenario cash flow table |
| 💰 **Mortgage Calculator** | 4 down-payment scenarios, affordability thresholds |
| 🏘️ **Neighborhood Analysis** | Schools, safety, walkability, amenities, growth |
| 📈 **Market Conditions** | Seller's/buyer's market, price trends, 12-month forecast |
| 💼 **Investment Strategies** | Buy & Hold vs BRRRR vs Fix & Flip comparison |
| 🔨 **Fix & Flip Analysis** | Rehab budget breakdown, 70% rule check, ROI |
| 🏢 **Commercial Analysis** | NOI, cap rate, DSCR, lease type, tenant quality |
| ⚖️ **Property Comparison** | Subject property vs 2 comparable alternatives |
| 📝 **MLS Listing** | 4 buyer-profile listing descriptions + headline options |
| 🔍 **Full Property Analysis** | Weighted composite score (0–100) + 90-day action plan |

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

# Optional — enables live web search for more accurate data
TAVILY_API_KEY=tvly-...
```

### 4. Launch

```powershell
streamlit run main.py
```

App opens at **http://localhost:8501**

---

## 🖥️ UI Walkthrough

```
┌─────────────────────────────┬──────────────────────────────────────────┐
│  Sidebar                    │  Main Area                               │
│  ─────────────────────────  │  ──────────────────────────────────────  │
│  🔑 OpenAI API Key          │  ✅ Analyses Complete  ⚠️ Errors  📥 PDF  │
│  🔑 Tavily API Key (opt.)   │                                          │
│  🏠 Property Address        │  [Full Report] [Quick] [Comps] [Rental]  │
│                             │   ← tabs, one per completed module →     │
│  📋 Analysis Modules        │                                          │
│   ☑ All / Core Only         │  # 🏡 Real Estate Report                │
│   ☑ Quick Snapshot (forced) │  ## 123 Main St, Austin TX               │
│   ☑ Property Screen (forced)│                                          │
│   ☑ Comparable Sales        │  ## 🔍 Full Property Analysis            │
│   ☑ Rental & Cash Flow      │  **Property Score:** 78/100  Grade: A    │
│   ☑ Mortgage Calculator     │  **Signal:** BUY                         │
│   ☑ Neighborhood Analysis   │  ...                                     │
│   ☑ Market Conditions       │                                          │
│   ☑ Investment Strategies   │  📋 Execution Log ▼                     │
│   ☑ Fix & Flip Analysis     │  📍 Parsing address...                   │
│   ☑ Commercial Analysis     │  ✅ quick complete                       │
│   ☑ Property Comparison     │  ✅ screen complete                      │
│   ☑ MLS Listing             │  ✅ comps complete                       │
│   ☑ Full Analysis           │  ...                                     │
│                             │                                          │
│  [🚀 Generate Report]       │                                          │
└─────────────────────────────┴──────────────────────────────────────────┘
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
               ┌──────┬──────┬─────────┬─────────┬────────┐
               ▼      ▼      ▼         ▼         ▼        ▼
             comps  rental  neighbor  mortgage  market  ...8 more
               │      │      │         │         │        │
               └──────┴──────┴────┬────┴─────────┴────────┘
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
- The singleton `get_graph()` compiles the graph once and reuses it

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
│
├── tools/
│   ├── __init__.py            # TOOL_REGISTRY dict + get_tool() factory
│   ├── base.py                # BaseRealEstateTool ABC (retry, score parsing)
│   ├── validation.py          # QuickTool, ScreenTool
│   ├── property_analysis.py   # CompsTool, RentalTool, MortgageTool
│   ├── location_tools.py      # NeighborhoodTool, MarketTool, ListingTool
│   └── investment_tools.py    # InvestTool, FlipTool, CommercialTool,
│                              # AnalyzeTool, CompareTool
│
├── tests/
│   ├── conftest.py            # Shared fixtures (mock_llm, sample_address)
│   ├── test_config.py         # Config and skill registry tests
│   ├── test_state.py          # Reducer and Pydantic model tests
│   ├── test_tools.py          # All 13 tool wrappers (22 tests)
│   ├── test_utils.py          # PDF generation + report formatting (6 tests)
│   └── test_graph.py          # LangGraph workflow tests (5 tests)
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

Expected: **42 passed**

Tests use `pytest-mock` to stub out OpenAI calls — no API key required to run the test suite.

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
| `PDF_OUTPUT_DIR` | `reports/` | Where generated PDFs are saved |

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
SKILL_LABELS["custom"] = "Custom Analysis"
```

The graph picks it up automatically — no graph changes needed.

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

---

## ⚠️ Disclaimer

This application uses AI to generate real estate analysis for **educational and research purposes only**. Output is based on the model's training data and does not reflect real-time MLS, tax, or market data.

**Always consult a licensed real estate professional, attorney, and/or financial advisor before making any investment decisions.**

---

## 📄 License

MIT
