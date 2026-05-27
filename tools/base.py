"""
tools/base.py — Abstract base class for all real estate tool wrappers.

Each tool:
  1. Has a skill_name and system_prompt class attribute.
  2. Implements run(address, **kwargs) -> dict.
  3. Uses _call_llm() which invokes ChatOpenAI with retry logic.
  4. Returns a dict matching ToolResult schema:
     {skill, address, output, score, grade, status, error}
"""
from __future__ import annotations
import re
import logging
from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

import config

logger = logging.getLogger(__name__)


class BaseRealEstateTool(ABC):
    """Abstract base for all real estate skill wrappers."""

    skill_name: str = "base"
    system_prompt: str = ""

    def __init__(self, llm: Optional[ChatOpenAI] = None) -> None:
        self.llm = llm or ChatOpenAI(
            model=config.OPENAI_MODEL,
            api_key=config.OPENAI_API_KEY,
            max_tokens=config.OPENAI_MAX_TOKENS,
            temperature=config.OPENAI_TEMPERATURE,
        )

    @abstractmethod
    def run(self, address: str, **kwargs) -> dict:
        """Execute the skill and return a result dict."""
        ...

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _call_llm_with_retry(self, system: str, user: str) -> str:
        """Internal retry-decorated LLM call."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
        response = self.llm.invoke(messages)
        return response.content

    def _call_llm(self, system: str, user: str) -> str:
        """Call ChatOpenAI with retry on transient errors.

        Unwraps tenacity RetryError so callers see the original exception.
        """
        try:
            return self._call_llm_with_retry(system, user)
        except RetryError as exc:
            # Re-raise the last underlying exception so callers see the real error.
            raise exc.last_attempt.exception() from exc

    def _extract_score(self, text: str) -> Optional[int]:
        """Parse 'Score: 72' or '72/100' from markdown text."""
        match = re.search(r"(?:score[:\s]+)?(\d{1,3})\s*/?\s*100", text, re.I)
        if match:
            val = int(match.group(1))
            return val if 0 <= val <= 100 else None
        return None

    def _score_to_grade(self, score: Optional[int]) -> Optional[str]:
        if score is None:
            return None
        if score >= 85: return "A+"
        if score >= 70: return "A"
        if score >= 55: return "B"
        if score >= 40: return "C"
        if score >= 25: return "D"
        return "F"

    def _error_result(self, address: str, error: str) -> dict:
        return {
            "skill": self.skill_name,
            "address": address,
            "output": f"⚠️ **{self.skill_name} failed:** {error}",
            "score": None,
            "grade": None,
            "status": "error",
            "error": error,
        }

    def _success_result(self, address: str, output: str) -> dict:
        score = self._extract_score(output)
        return {
            "skill": self.skill_name,
            "address": address,
            "output": output,
            "score": score,
            "grade": self._score_to_grade(score),
            "status": "success",
            "error": None,
        }
