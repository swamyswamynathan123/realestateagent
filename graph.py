"""
graph.py — LangGraph StateGraph for the Real Estate Agent App.

Execution order:
  1. parse_address      (sequential)
  2. run_quick          (sequential — validation phase)
  3. run_screen         (sequential — validation phase)
  4. check_valid        (conditional: proceed or early-exit to generate_report)
  5. [parallel fan-out via Send to all selected parallel skills]
  6. aggregate_results  (fan-in — waits for all parallel nodes to complete)
  7. generate_report    (sequential)
  8. generate_pdf       (sequential)
  9. END
"""
from __future__ import annotations
import logging
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from state import RealEstateState
from tools import get_tool
from config import PARALLEL_SKILLS
import utils

logger = logging.getLogger(__name__)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _run_tool(skill_name: str, state: RealEstateState) -> dict:
    """Invoke a named tool and return the appropriate state delta."""
    address = state["address"]
    try:
        tool = get_tool(skill_name)
        result = tool.run(address)
        if result["status"] == "error":
            return {
                "errors": {skill_name: result.get("error", "Unknown error")},
                "progress": [f"⚠️ {skill_name} failed: {result.get('error', '')}"],
            }
        return {
            "tool_results": {skill_name: result["output"]},
            "progress": [f"✅ {skill_name} complete"],
        }
    except Exception as e:
        msg = str(e)
        logger.exception("Unhandled error in skill: %s", skill_name)
        return {
            "errors": {skill_name: msg},
            "progress": [f"❌ {skill_name} error: {msg}"],
        }


# ── Nodes ──────────────────────────────────────────────────────────────────────

def parse_address(state: RealEstateState) -> dict:
    """Parse and normalise the address string."""
    address = state["address"].strip()
    return {
        "address": address,
        "parsed_data": {"raw": address, "normalised": address},
        "progress": [f"📍 Parsing address: {address}"],
    }


def run_quick(state: RealEstateState) -> dict:
    """Run the quick snapshot tool."""
    delta = _run_tool("quick", state)
    return delta


def run_screen(state: RealEstateState) -> dict:
    """Run the screen tool and set validation_passed flag."""
    address = state["address"]
    try:
        tool = get_tool("screen")
        result = tool.run(address)
        passed = result.get("validation_passed", True)
        delta: dict = {
            "validation_passed": passed,
            "progress": [
                f"{'✅' if passed else '❌'} screen "
                f"{'passed' if passed else 'FAILED — address invalid'}"
            ],
        }
        if result["status"] == "success":
            delta["tool_results"] = {"screen": result["output"]}
        else:
            delta["errors"] = {"screen": result.get("error", "screen error")}
        return delta
    except Exception as e:
        return {
            "validation_passed": False,
            "errors": {"screen": str(e)},
            "progress": [f"❌ screen error: {e}"],
        }


def run_parallel_skill(state: RealEstateState) -> dict:
    """
    Generic node for parallel skills.
    The skill name is passed via state['_current_skill'] by the Send dispatcher.
    """
    skill_name = state.get("_current_skill", "unknown")  # type: ignore[call-overload]
    return _run_tool(skill_name, state)


def aggregate_results(state: RealEstateState) -> dict:
    """Fan-in: all parallel nodes have completed; log summary."""
    n_success = len(state.get("tool_results", {}))
    n_error = len(state.get("errors", {}))
    return {
        "progress": [f"🔀 Aggregated {n_success} results, {n_error} errors"],
    }


def generate_report(state: RealEstateState) -> dict:
    """Combine all outputs into a unified markdown report."""
    address = state["address"]
    tool_results = state.get("tool_results", {})
    errors = state.get("errors", {})

    # If validation failed (early exit), add a clear error message
    if not state.get("validation_passed", True):
        report = (
            f"# ⚠️ Address Validation Failed\n\n"
            f"**Address:** {address}\n\n"
            "The property screen determined this address could not be validated as a real US property.\n\n"
            "**Please try:**\n"
            "- Entering the full address including city, state, and ZIP\n"
            "- Verifying the street number and name\n"
            "- Using a real US property address\n"
        )
    else:
        report = utils.format_final_report(address, tool_results, errors)

    return {
        "final_report": report,
        "progress": ["📄 Final report generated"],
    }


def generate_pdf(state: RealEstateState) -> dict:
    """Render the final report to PDF."""
    try:
        pdf_path = utils.generate_pdf_report(
            state["final_report"],
            state["address"],
        )
        return {
            "pdf_path": pdf_path,
            "progress": [f"📑 PDF saved: {pdf_path}"],
        }
    except Exception as e:
        logger.exception("PDF generation failed")
        return {
            "pdf_path": None,
            "progress": [f"⚠️ PDF generation failed: {e}"],
        }


# ── Routing ────────────────────────────────────────────────────────────────────

def route_after_screen(state: RealEstateState) -> list[Send] | str:
    """
    If validation passed: fan out to selected parallel skills via Send.
    If validation failed: short-circuit to generate_report.
    """
    if not state.get("validation_passed", False):
        return "generate_report"

    selected = state.get("selected_skills", [])
    parallel_selected = [s for s in selected if s in PARALLEL_SKILLS]

    if not parallel_selected:
        # No parallel skills selected — go straight to aggregate
        return "aggregate_results"

    # Fan out: inject _current_skill into each sub-state
    sends = []
    for skill in parallel_selected:
        skill_state = dict(state)
        skill_state["_current_skill"] = skill  # type: ignore[assignment]
        sends.append(Send("run_parallel_skill", skill_state))
    return sends


# ── Graph Builder ──────────────────────────────────────────────────────────────

def build_graph() -> Any:
    """Compile and return the LangGraph StateGraph."""
    builder = StateGraph(RealEstateState)

    # Register nodes
    builder.add_node("parse_address", parse_address)
    builder.add_node("run_quick", run_quick)
    builder.add_node("run_screen", run_screen)
    builder.add_node("run_parallel_skill", run_parallel_skill)
    builder.add_node("aggregate_results", aggregate_results)
    builder.add_node("generate_report", generate_report)
    builder.add_node("generate_pdf", generate_pdf)

    # Sequential: start → parse → quick → screen
    builder.add_edge(START, "parse_address")
    builder.add_edge("parse_address", "run_quick")
    builder.add_edge("run_quick", "run_screen")

    # Conditional fan-out after screen
    # route_after_screen returns either a string node name or a list of Send objects
    builder.add_conditional_edges(
        "run_screen",
        route_after_screen,
        # path_map for string returns; Send objects bypass this
        {
            "generate_report": "generate_report",
            "aggregate_results": "aggregate_results",
        },
    )

    # Fan-in: all parallel_skill nodes flow into aggregate_results
    builder.add_edge("run_parallel_skill", "aggregate_results")

    # Tail: aggregate → report → pdf → END
    builder.add_edge("aggregate_results", "generate_report")
    builder.add_edge("generate_report", "generate_pdf")
    builder.add_edge("generate_pdf", END)

    return builder.compile()


# ── Singleton compiled graph ───────────────────────────────────────────────────

_compiled_graph = None


def get_graph() -> Any:
    """Return cached compiled graph (created on first call)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
