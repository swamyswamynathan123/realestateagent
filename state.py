"""
state.py — LangGraph state definition and Pydantic result model.
"""
from __future__ import annotations
from typing import Annotated, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# ── Reducers ───────────────────────────────────────────────────────────────────

def merge_dicts(left: dict, right: dict) -> dict:
    """Merge-right reducer for parallel node outputs."""
    return {**left, **right}


def append_list(left: list, right: list) -> list:
    """Concatenation reducer for progress log."""
    return left + right


# ── Pydantic result model ──────────────────────────────────────────────────────

class ToolResult(BaseModel):
    skill: str
    address: str
    output: str = Field(description="Markdown-formatted analysis")
    score: Optional[int] = Field(None, ge=0, le=100)
    grade: Optional[str] = None       # A+, A, B, C, D, F
    status: str = "success"           # "success" | "error"
    error: Optional[str] = None


# ── LangGraph state ────────────────────────────────────────────────────────────

class RealEstateState(TypedDict):
    # Input
    address: str
    selected_skills: list[str]

    # Parsed address components (set by parse_address node)
    parsed_data: dict

    # Parallel-safe result stores (reducer merges concurrent writes)
    tool_results: Annotated[dict[str, str], merge_dicts]   # skill -> markdown
    errors: Annotated[dict[str, str], merge_dicts]          # skill -> error msg

    # Control flow
    validation_passed: bool

    # Final outputs
    final_report: str
    pdf_path: Optional[str]

    # UI streaming
    progress: Annotated[list[str], append_list]
