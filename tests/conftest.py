import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_llm(mocker):
    """Returns a mock ChatOpenAI that echoes back a canned markdown string."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content="# Mock Analysis\n\n**Score:** 75/100\n**Grade:** A"
    )
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
