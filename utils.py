"""
utils.py — Report formatting, PDF generation, retry helpers.
"""
from __future__ import annotations
import functools
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Geocoding ──────────────────────────────────────────────────────────────────

_GEO_HEADERS = {"User-Agent": "RealEstateAgent/1.0 (educational)"}
_GEO_TIMEOUT = 6


def _nominatim(query: str) -> Optional[tuple[float, float]]:
    """Try Nominatim (OpenStreetMap) for *query*.  Returns (lat, lon) or None."""
    try:
        import requests
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
            headers=_GEO_HEADERS,
            timeout=_GEO_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        logger.debug("Nominatim failed for: %.60s", query, exc_info=True)
    return None


def _photon(query: str) -> Optional[tuple[float, float]]:
    """Try Photon (komoot.io, OSM-based) as a secondary geocoder."""
    try:
        import requests
        r = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": query, "limit": 1, "lang": "en"},
            headers=_GEO_HEADERS,
            timeout=_GEO_TIMEOUT,
        )
        r.raise_for_status()
        features = r.json().get("features", [])
        if features:
            lon, lat = features[0]["geometry"]["coordinates"]
            return float(lat), float(lon)
    except Exception:
        logger.debug("Photon failed for: %.60s", query, exc_info=True)
    return None


def _broad_query(address: str) -> str:
    """
    Strip the street number/name and return the city-level part of the address.

    "123 Main St, Austin, TX 78701" → "Austin, TX 78701"
    Falls back to the original address if no comma is found.
    """
    parts = [p.strip() for p in address.split(",")]
    # Drop the first segment (street) if there are 3+ parts
    if len(parts) >= 3:
        return ", ".join(parts[1:])
    if len(parts) == 2:
        return parts[1]
    return address


@functools.lru_cache(maxsize=200)
def geocode_address(address: str) -> Optional[tuple[float, float]]:
    """
    Convert a US property address to (latitude, longitude).  No API key required.

    Uses a three-step chain to maximise hit rate:
      1. Nominatim (OSM) — best for exact matches in OSM database
      2. Photon (komoot) — different OSM index, better for partial addresses
      3. City/state/zip fallback — shows the general area when the exact
         street address isn't in either database (e.g. new construction,
         rural properties, fictional addresses)

    Returns None only if all three strategies fail.
    """
    # 1. Exact address via Nominatim
    result = _nominatim(address)
    if result:
        return result

    # 2. Exact address via Photon
    result = _photon(address)
    if result:
        return result

    # 3. City-level fallback (drops street number/name)
    broad = _broad_query(address)
    if broad != address:
        result = _nominatim(broad) or _photon(broad)
        if result:
            logger.info("Geocoded at city level (street not found): %s → %s", address, broad)
            return result

    logger.warning("All geocoding strategies failed for: %.80s", address)
    return None

# ── Section ordering for final report ──────────────────────────────────────────

SECTION_ORDER = [
    "analyze", "quick", "screen",
    "comps", "rental", "mortgage",
    "neighborhood", "market",
    "invest", "flip", "commercial", "compare",
    "listing",
]

SECTION_TITLES = {
    "analyze":      "🔍 Full Property Analysis",
    "quick":        "⚡ Quick Snapshot",
    "screen":       "📋 Property Screen",
    "comps":        "📊 Comparable Sales",
    "rental":       "🏠 Rental & Cash Flow",
    "mortgage":     "💰 Mortgage Calculator",
    "neighborhood": "🏘️ Neighborhood Analysis",
    "market":       "📈 Market Conditions",
    "invest":       "💼 Investment Strategies",
    "flip":         "🔨 Fix & Flip Analysis",
    "commercial":   "🏢 Commercial Analysis",
    "compare":      "⚖️ Property Comparison",
    "listing":      "📝 MLS Listing Descriptions",
}


def format_final_report(
    address: str,
    tool_results: dict[str, str],
    errors: dict[str, str],
) -> str:
    """Combine all tool outputs into a single unified markdown report."""
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    lines = [
        "# 🏡 Real Estate Report",
        f"## {address}",
        f"*Generated on {now}*",
        "",
        "---",
        "",
    ]

    # Add sections in defined order
    for skill in SECTION_ORDER:
        if skill in tool_results:
            title = SECTION_TITLES.get(skill, skill.title())
            lines.append(f"## {title}")
            lines.append("")
            lines.append(tool_results[skill])
            lines.append("")
            lines.append("---")
            lines.append("")

    # Error summary at the end
    if errors:
        lines.append("## ⚠️ Analysis Errors")
        lines.append("")
        for skill, error in errors.items():
            lines.append(f"- **{skill}**: {error} *(section skipped)*")
        lines.append("")

    lines.append("*This report was generated by AI for educational purposes only.*")
    lines.append("*Always consult a licensed real estate professional before making investment decisions.*")

    return "\n".join(lines)


def generate_pdf_report(
    markdown_content: str,
    address: str,
    output_dir: str = "reports",
) -> str:
    """
    Convert markdown report to PDF using ReportLab.
    Returns the absolute path to the generated PDF file.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    )

    # Ensure output dir exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate filename
    safe_addr = re.sub(r"[^\w\s-]", "", address).strip().replace(" ", "_")[:40]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PROPERTY_REPORT_{safe_addr}_{timestamp}.pdf"
    pdf_path = os.path.join(output_dir, filename)

    # Build PDF
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#1a3c5e"),
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2d6a9f"),
        spaceBefore=16,
        spaceAfter=6,
    )
    h3_style = ParagraphStyle(
        "CustomH3",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#1a3c5e"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=14,
        spaceAfter=4,
    )

    def safe_text(text: str) -> str:
        """Escape special XML chars for ReportLab."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

    story = []

    for line in markdown_content.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 4))
            continue

        if stripped.startswith("# "):
            story.append(Paragraph(safe_text(stripped[2:]), title_style))
        elif stripped.startswith("## "):
            story.append(HRFlowable(width="100%", thickness=1,
                                     color=colors.HexColor("#2d6a9f")))
            story.append(Paragraph(safe_text(stripped[3:]), h2_style))
        elif stripped.startswith("### "):
            story.append(Paragraph(safe_text(stripped[4:]), h3_style))
        elif stripped.startswith("---"):
            story.append(Spacer(1, 6))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            bullet = "• " + safe_text(stripped[2:])
            story.append(Paragraph(bullet, body_style))
        else:
            # Handle inline bold: **text**
            formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe_text(stripped))
            story.append(Paragraph(formatted, body_style))

    doc.build(story)
    logger.info("PDF generated: %s", pdf_path)
    return pdf_path
