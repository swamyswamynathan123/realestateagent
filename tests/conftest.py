import pytest
from unittest.mock import MagicMock


_MOCK_CONTENT = """\
# Mock Analysis

### Comparable Sales (5 comps)
| # | Address | Sale Price | Sq Ft | $/Sq Ft | Distance | Days Ago | Similarity |
|---|---------|-----------|-------|---------|----------|----------|------------|
| 1 | 100 Oak Ave | $420,000 | 1,800 | $233 | 0.3 mi | 14 | High |
| 2 | 200 Elm St  | $405,000 | 1,750 | $231 | 0.5 mi | 30 | High |
| 3 | 300 Pine Rd | $435,000 | 1,900 | $229 | 0.7 mi | 45 | Med  |
| 4 | 400 Maple Dr| $398,000 | 1,700 | $234 | 1.1 mi | 60 | Med  |
| 5 | 500 Cedar Ln| $450,000 | 1,950 | $231 | 1.4 mi | 75 | Low  |

**Score:** 75/100
**Grade:** A
"""


@pytest.fixture
def mock_llm(mocker):
    """Returns a mock ChatOpenAI that echoes back a canned markdown string.

    The response includes a properly-formatted 5-row comparable sales table so
    CompsTool._ensure_five_comps() is satisfied without firing a second call.
    """
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=_MOCK_CONTENT)
    return llm


@pytest.fixture
def sample_address():
    return "123 Main St, Austin, TX 78701"


@pytest.fixture
def sample_state(sample_address):
    from state import RealEstateState
    return {
        "address": sample_address,
        "selected_skills": ["quick", "screen", "comps"],
        "parsed_data": {},
        "tool_results": {},
        "errors": {},
        "validation_passed": False,
        "final_report": "",
        "pdf_path": None,
        "progress": [],
    }
