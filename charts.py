"""
charts.py — Plotly chart helpers for the Real Estate Agent UI.

All functions return a Plotly Figure object ready for st.plotly_chart().

Charts:
  score_radar()      — Radar chart of per-skill scores
  cashflow_waterfall()— Waterfall chart of monthly cash flow components
  comp_prices_bar()  — Horizontal bar chart of comparable sale prices
"""
from __future__ import annotations
import re
from typing import Optional


# ── Score Radar ────────────────────────────────────────────────────────────────

_RADAR_SKILL_ORDER = [
    "quick", "screen", "comps", "rental", "mortgage",
    "neighborhood", "market", "invest", "flip",
    "commercial", "analyze", "compare", "listing",
    "str", "tax",
]

_RADAR_LABELS = {
    "quick":        "Quick",
    "screen":       "Screen",
    "comps":        "Comps",
    "rental":       "Rental",
    "mortgage":     "Mortgage",
    "neighborhood": "Neighborhood",
    "market":       "Market",
    "invest":       "Invest",
    "flip":         "Flip",
    "commercial":   "Commercial",
    "analyze":      "Analysis",
    "compare":      "Compare",
    "listing":      "Listing",
    "str":          "STR",
    "tax":          "Tax",
}


def _extract_score(text: str) -> Optional[int]:
    m = re.search(r"(?:score[:\s]+)?(\d{1,3})\s*/?\s*100", text, re.I)
    if m:
        val = int(m.group(1))
        return val if 0 <= val <= 100 else None
    return None


def score_radar(tool_results: dict[str, str], address: str = ""):
    """Return a Plotly radar/spider chart of skill scores.

    Only includes skills that have a parseable Score: XX/100 in their output.
    Requires plotly to be installed.
    """
    import plotly.graph_objects as go

    scores: dict[str, int] = {}
    for skill, md in tool_results.items():
        s = _extract_score(md)
        if s is not None:
            scores[skill] = s

    if not scores:
        return None

    # Order skills consistently
    ordered = [s for s in _RADAR_SKILL_ORDER if s in scores]
    # Any skill not in the predefined order goes at the end
    ordered += [s for s in scores if s not in ordered]

    labels = [_RADAR_LABELS.get(s, s) for s in ordered]
    values = [scores[s] for s in ordered]
    # Close the polygon
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            fillcolor="rgba(45, 106, 159, 0.25)",
            line=dict(color="#2d6a9f", width=2),
            name="Score",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=10)),
        ),
        showlegend=False,
        title=dict(
            text=f"Score Dashboard{' — ' + address if address else ''}",
            font=dict(size=14, color="#1a3c5e"),
        ),
        margin=dict(l=60, r=60, t=60, b=40),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Cash Flow Waterfall ────────────────────────────────────────────────────────

def cashflow_waterfall(tool_results: dict[str, str]):
    """Return a Plotly waterfall chart parsed from the rental tool output.

    Parses the Monthly Cash Flow table from the rental markdown, or uses
    sensible demo values if parsing fails.
    """
    import plotly.graph_objects as go

    # Try to parse cash flow items from rental markdown
    items: list[tuple[str, float]] = []
    rental_md = tool_results.get("rental", "")

    if rental_md:
        # Look for table rows: | Item | Amount |
        # Matches lines like "| Gross Rent | $2,500 |" or "| Vacancy (8%) | -$200 |"
        for line in rental_md.split("\n"):
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) < 2:
                continue
            label, amount_str = parts[0], parts[1]
            # Skip header/separator rows
            if label.startswith("-") or label.lower() in ("item", "amount"):
                continue
            # Clean bold markers
            label = label.strip("*").strip()
            amount_str = amount_str.strip("*").strip()
            # Parse dollar amount
            m = re.search(r"(-?\$?[\d,]+)", amount_str)
            if not m:
                continue
            raw = m.group(1).replace("$", "").replace(",", "")
            try:
                val = float(raw)
            except ValueError:
                continue
            if val == 0:
                continue
            items.append((label, val))

    # Fallback demo data if parsing yielded nothing useful
    if len(items) < 3:
        items = [
            ("Gross Rent",         2_500),
            ("Vacancy (8%)",        -200),
            ("Mortgage (P&I)",    -1_400),
            ("Property Tax",        -250),
            ("Insurance",           -100),
            ("Maintenance (5%)",    -125),
            ("Property Mgmt (10%)", -250),
            ("CapEx Reserve",       -125),
        ]

    labels = [i[0] for i in items]
    values = [i[1] for i in items]

    # Determine measure type per bar
    measures = []
    for v in values:
        if "net" in labels[values.index(v)].lower() or "total" in labels[values.index(v)].lower():
            measures.append("total")
        else:
            measures.append("relative")
    # Last item is always total
    measures[-1] = "total"

    colors = ["#2d6a9f" if v > 0 else "#e05c5c" for v in values]
    # Total bars are gold
    for i, m in enumerate(measures):
        if m == "total":
            colors[i] = "#f0a500" if values[i] >= 0 else "#e05c5c"

    fig = go.Figure(
        go.Waterfall(
            name="Cash Flow",
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            text=[f"${v:,.0f}" for v in values],
            textposition="outside",
            connector=dict(line=dict(color="#cccccc", width=1)),
            increasing=dict(marker=dict(color="#2d6a9f")),
            decreasing=dict(marker=dict(color="#e05c5c")),
            totals=dict(marker=dict(color="#f0a500")),
        )
    )
    fig.update_layout(
        title=dict(
            text="Monthly Cash Flow Breakdown",
            font=dict(size=14, color="#1a3c5e"),
        ),
        yaxis=dict(title="$ / month", tickformat="$,.0f"),
        xaxis=dict(tickangle=-30),
        height=380,
        margin=dict(l=60, r=20, t=60, b=100),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
    )
    return fig


# ── Comp Prices Bar ────────────────────────────────────────────────────────────

def comp_prices_bar(tool_results: dict[str, str]):
    """Return a horizontal bar chart of comparable sale prices.

    Parses the Comparable Sales table from the comps markdown.
    Falls back to demo data if the table cannot be parsed.
    """
    import plotly.graph_objects as go

    comps_md = tool_results.get("comps", "")

    addresses: list[str] = []
    prices: list[float] = []

    if comps_md:
        in_table = False
        for line in comps_md.split("\n"):
            if "|" not in line:
                in_table = False
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if not parts:
                continue
            # Detect header row
            if any(h in parts[0].lower() for h in ("address", "#", "comp")):
                in_table = True
                continue
            if parts[0].startswith("-"):
                continue
            if not in_table:
                continue
            if len(parts) < 2:
                continue
            addr = parts[0].strip("*").strip()[:30]
            # Find price column (first column that looks like a dollar amount)
            price_val: Optional[float] = None
            for p in parts[1:]:
                m = re.search(r"\$?([\d,]+)", p.replace(",", ""))
                if m:
                    raw = int(m.group(1).replace(",", ""))
                    if raw > 50_000:   # plausible property price
                        price_val = float(raw)
                        break
            if addr and price_val:
                addresses.append(addr)
                prices.append(price_val)

    # Fallback
    if len(prices) < 2:
        addresses = ["100 Oak Ave", "200 Elm St", "300 Pine Rd", "400 Maple Dr", "500 Cedar Ln"]
        prices    = [420_000, 405_000, 435_000, 398_000, 450_000]

    # Sort ascending for readability
    pairs = sorted(zip(prices, addresses), reverse=False)
    prices_s = [p for p, _ in pairs]
    addrs_s  = [a for _, a in pairs]

    colors = ["#2d6a9f"] * len(prices_s)

    fig = go.Figure(
        go.Bar(
            x=prices_s,
            y=addrs_s,
            orientation="h",
            marker=dict(color=colors),
            text=[f"${p:,.0f}" for p in prices_s],
            textposition="auto",
        )
    )
    fig.update_layout(
        title=dict(
            text="Comparable Sale Prices",
            font=dict(size=14, color="#1a3c5e"),
        ),
        xaxis=dict(title="Sale Price ($)", tickformat="$,.0f"),
        height=340,
        margin=dict(l=120, r=20, t=60, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
    )
    return fig
