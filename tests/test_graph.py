import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_all_tools(mocker):
    """Patch get_tool to return a mock that succeeds for all skills."""
    success_result = {
        "skill": "mock",
        "address": "123 Main St, Austin TX",
        "output": "# Mock Analysis\n\n**Score:** 75/100",
        "score": 75,
        "grade": "A",
        "status": "success",
        "error": None,
        "validation_passed": True,
    }

    def make_mock_tool(skill_name):
        m = MagicMock()
        result = {**success_result, "skill": skill_name}
        if skill_name == "screen":
            result["validation_passed"] = True
        m.run.return_value = result
        return m

    mocker.patch("graph.get_tool", side_effect=make_mock_tool)
    return success_result


@pytest.fixture
def initial_state():
    return {
        "address": "123 Main St, Austin TX",
        "selected_skills": ["quick", "screen", "comps", "rental"],
        "parsed_data": {},
        "tool_results": {},
        "errors": {},
        "validation_passed": False,
        "final_report": "",
        "pdf_path": None,
        "progress": [],
    }


def test_graph_compiles():
    """Graph must compile without errors."""
    from graph import build_graph
    g = build_graph()
    assert g is not None


def test_graph_runs_valid_address(mock_all_tools, initial_state):
    """Full run with valid address should produce a report."""
    from graph import build_graph
    g = build_graph()
    final = None
    for event in g.stream(initial_state, stream_mode="values"):
        final = event
    assert final is not None
    assert final["validation_passed"] is True
    assert len(final["final_report"]) > 50


def test_graph_early_exit_on_invalid_address(mocker, initial_state):
    """When screen fails validation, parallel skills should not run."""
    def make_mock_tool(skill_name):
        m = MagicMock()
        if skill_name == "screen":
            m.run.return_value = {
                "skill": "screen", "address": "asdf",
                "output": "VALIDATION_FAILED: Not a real address",
                "score": None, "grade": None,
                "status": "success", "error": None,
                "validation_passed": False,
            }
        else:
            m.run.return_value = {
                "skill": skill_name, "address": "asdf",
                "output": f"# {skill_name} analysis",
                "score": 70, "grade": "A",
                "status": "success", "error": None,
                "validation_passed": True,
            }
        return m

    mocker.patch("graph.get_tool", side_effect=make_mock_tool)

    from graph import build_graph
    g = build_graph()
    invalid_state = {**initial_state, "address": "asdf"}
    final = None
    for event in g.stream(invalid_state, stream_mode="values"):
        final = event

    assert final is not None
    # comps should NOT have run (validation failed before fan-out)
    assert "comps" not in final.get("tool_results", {})
    # Final report should mention validation failure
    assert "Validation" in final["final_report"] or "validation" in final["final_report"]


def test_graph_handles_tool_error_gracefully(mocker, initial_state):
    """A tool error should go to errors dict, not crash the graph."""
    def make_mock_tool(skill_name):
        m = MagicMock()
        if skill_name == "comps":
            m.run.return_value = {
                "skill": "comps", "address": "123 Main St",
                "output": "⚠️ comps failed",
                "score": None, "grade": None,
                "status": "error", "error": "API timeout",
                "validation_passed": True,
            }
        elif skill_name == "screen":
            m.run.return_value = {
                "skill": "screen", "address": "123 Main St",
                "output": "# Screen", "score": 75, "grade": "A",
                "status": "success", "error": None,
                "validation_passed": True,
            }
        else:
            m.run.return_value = {
                "skill": skill_name, "address": "123 Main St",
                "output": f"# {skill_name}", "score": 75, "grade": "A",
                "status": "success", "error": None,
                "validation_passed": True,
            }
        return m

    mocker.patch("graph.get_tool", side_effect=make_mock_tool)

    from graph import build_graph
    g = build_graph()
    final = None
    for event in g.stream(initial_state, stream_mode="values"):
        final = event

    assert final is not None
    # Graph should complete even with one tool error
    assert len(final["final_report"]) > 50
    # comps error should be captured
    assert "comps" in final.get("errors", {})


def test_graph_respects_selected_skills(mock_all_tools, initial_state):
    """Only selected skills should appear in tool_results."""
    from graph import build_graph
    g = build_graph()
    # Only request quick + screen (sequential) + comps (parallel)
    state = {**initial_state, "selected_skills": ["quick", "screen", "comps"]}
    final = None
    for event in g.stream(state, stream_mode="values"):
        final = event

    assert final is not None
    # rental was not selected, should not be in results
    assert "rental" not in final.get("tool_results", {})
