import os
import tempfile
import pytest


def test_format_report_combines_sections():
    from utils import format_final_report
    tool_results = {
        "quick": "# Quick\nScore: 75/100",
        "comps": "# Comps\nScore: 80/100",
    }
    report = format_final_report("123 Main St, Austin TX", tool_results, {})
    assert "123 Main St" in report
    assert "Quick Snapshot" in report  # uses SECTION_TITLES
    assert "Comparable Sales" in report
    assert "75/100" in report


def test_format_report_orders_sections_correctly():
    from utils import format_final_report, SECTION_ORDER
    tool_results = {skill: f"content for {skill}" for skill in ["comps", "quick", "analyze"]}
    report = format_final_report("123 Main", tool_results, {})
    # "analyze" should appear before "quick" before "comps" per SECTION_ORDER
    pos_analyze = report.find("Full Property Analysis")
    pos_quick = report.find("Quick Snapshot")
    pos_comps = report.find("Comparable Sales")
    assert pos_analyze < pos_quick < pos_comps


def test_format_report_includes_error_section():
    from utils import format_final_report
    report = format_final_report("123 Main", {}, {"comps": "API timeout"})
    assert "Analysis Errors" in report
    assert "comps" in report
    assert "API timeout" in report


def test_format_report_skips_missing_skills():
    from utils import format_final_report
    report = format_final_report("123 Main", {"quick": "data"}, {})
    assert "Comparable Sales" not in report


def test_generate_pdf_creates_file():
    from utils import generate_pdf_report
    with tempfile.TemporaryDirectory() as tmpdir:
        content = "# Real Estate Report\n\n## Quick Analysis\n**Score:** 75/100\n\n### Details\nSome content here."
        path = generate_pdf_report(content, "123 Main St, Austin TX", output_dir=tmpdir)
        assert os.path.exists(path)
        assert path.endswith(".pdf")
        assert os.path.getsize(path) > 1000  # non-trivial PDF


def test_generate_pdf_filename_contains_address():
    from utils import generate_pdf_report
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_pdf_report("# Report", "456 Elm St, Dallas TX", output_dir=tmpdir)
        basename = os.path.basename(path)
        assert "456_Elm_St" in basename or "456" in basename
