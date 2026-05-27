import pytest
from unittest.mock import MagicMock


# ── Task 4: Base tool tests ────────────────────────────────────────────────────

def test_base_tool_calls_llm(mock_llm):
    from tools.base import BaseRealEstateTool

    class ConcreteTestTool(BaseRealEstateTool):
        skill_name = "test"
        system_prompt = "You are a test agent."

        def run(self, address: str, **kwargs) -> dict:
            output = self._call_llm(self.system_prompt, f"Analyze: {address}")
            return self._success_result(address, output)

    tool = ConcreteTestTool(llm=mock_llm)
    result = tool.run("123 Main St, Austin TX")
    assert result["status"] == "success"
    assert "Mock Analysis" in result["output"]
    mock_llm.invoke.assert_called_once()


def test_base_tool_handles_llm_error(mock_llm):
    from tools.base import BaseRealEstateTool

    mock_llm.invoke.side_effect = Exception("API timeout")

    class FailingTool(BaseRealEstateTool):
        skill_name = "failing"
        system_prompt = "You are a test agent."

        def run(self, address: str, **kwargs) -> dict:
            try:
                output = self._call_llm(self.system_prompt, address)
                return self._success_result(address, output)
            except Exception as e:
                return self._error_result(address, str(e))

    tool = FailingTool(llm=mock_llm)
    result = tool.run("123 Main St")
    assert result["status"] == "error"
    assert "API timeout" in result["error"]


def test_extract_score_parses_x_of_100(mock_llm):
    from tools.base import BaseRealEstateTool

    class MinimalTool(BaseRealEstateTool):
        skill_name = "minimal"
        def run(self, address, **kw): return {}

    tool = MinimalTool(llm=mock_llm)
    assert tool._extract_score("Score: 75/100") == 75
    assert tool._extract_score("**Score:** 82/100") == 82
    assert tool._extract_score("no score here") is None


def test_score_to_grade(mock_llm):
    from tools.base import BaseRealEstateTool

    class MinimalTool(BaseRealEstateTool):
        skill_name = "minimal"
        def run(self, address, **kw): return {}

    tool = MinimalTool(llm=mock_llm)
    assert tool._score_to_grade(90) == "A+"
    assert tool._score_to_grade(75) == "A"
    assert tool._score_to_grade(60) == "B"
    assert tool._score_to_grade(45) == "C"
    assert tool._score_to_grade(30) == "D"
    assert tool._score_to_grade(10) == "F"
    assert tool._score_to_grade(None) is None
