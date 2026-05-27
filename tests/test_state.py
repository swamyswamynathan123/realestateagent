from state import RealEstateState, merge_dicts, append_list, ToolResult


def test_merge_dicts_combines():
    a = {"comps": "result-a"}
    b = {"rental": "result-b"}
    assert merge_dicts(a, b) == {"comps": "result-a", "rental": "result-b"}


def test_merge_dicts_right_wins_on_conflict():
    a = {"comps": "old"}
    b = {"comps": "new"}
    assert merge_dicts(a, b)["comps"] == "new"


def test_append_list_concatenates():
    assert append_list([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_state_has_required_keys():
    state: RealEstateState = {
        "address": "123 Main St, Austin TX",
        "selected_skills": ["quick", "comps"],
        "parsed_data": {},
        "tool_results": {},
        "errors": {},
        "validation_passed": False,
        "final_report": "",
        "pdf_path": None,
        "progress": [],
    }
    assert state["address"] == "123 Main St, Austin TX"
    assert state["validation_passed"] is False


def test_tool_result_schema():
    r = ToolResult(
        skill="comps",
        address="123 Main St",
        output="# Comps\n...",
        score=72,
        grade="A",
        status="success",
        error=None,
    )
    assert r.status == "success"
    assert r.score == 72
    assert r.grade == "A"


def test_tool_result_optional_fields():
    r = ToolResult(skill="quick", address="123 Main", output="content")
    assert r.score is None
    assert r.grade is None
    assert r.status == "success"
    assert r.error is None
