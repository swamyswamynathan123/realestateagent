"""
history.py — Persistent report history using SQLite.

Each completed analysis is stored as a row:
  id, address, timestamp, report_markdown, tool_results_json, scores_json

Functions:
  save_report()   — insert or replace
  list_reports()  — return recent rows (metadata only, no markdown)
  load_report()   — return full row by id
  delete_report() — remove by id
  clear_history() — drop all rows
"""
from __future__ import annotations
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB = ".report_history.db"


def _db_path(db: str = _DEFAULT_DB) -> str:
    return db


@contextmanager
def _conn(db: str = _DEFAULT_DB):
    path = _db_path(db)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _ensure_table(db: str = _DEFAULT_DB) -> None:
    with _conn(db) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS report_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                address         TEXT    NOT NULL,
                timestamp       TEXT    NOT NULL,
                report_markdown TEXT    NOT NULL,
                tool_results    TEXT    NOT NULL DEFAULT '{}',
                scores          TEXT    NOT NULL DEFAULT '{}',
                purchase_price  INTEGER NOT NULL DEFAULT 0,
                hoa_fees        INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Index for fast recency queries
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_rh_timestamp
            ON report_history (timestamp DESC)
        """)
        # Migrate existing tables that predate purchase_price / hoa_fees columns
        for col, defn in [
            ("purchase_price", "INTEGER NOT NULL DEFAULT 0"),
            ("hoa_fees",       "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                con.execute(f"ALTER TABLE report_history ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass  # column already exists


def save_report(
    address: str,
    report_markdown: str,
    tool_results: dict[str, str],
    purchase_price: int = 0,
    hoa_fees: int = 0,
    db: str = _DEFAULT_DB,
) -> int:
    """Persist a completed analysis.  Returns the new row id."""
    _ensure_table(db)

    # Extract scores from each tool result
    import re
    scores: dict[str, int] = {}
    for skill, md in tool_results.items():
        m = re.search(r"(?:score[:\s]+)?(\d{1,3})\s*/?\s*100", md, re.I)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                scores[skill] = val

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn(db) as con:
        cur = con.execute(
            """
            INSERT INTO report_history
                (address, timestamp, report_markdown, tool_results, scores,
                 purchase_price, hoa_fees)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                address,
                ts,
                report_markdown,
                json.dumps(tool_results),
                json.dumps(scores),
                purchase_price,
                hoa_fees,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def list_reports(limit: int = 20, db: str = _DEFAULT_DB) -> list[dict]:
    """Return recent reports (metadata only — no full markdown)."""
    _ensure_table(db)
    with _conn(db) as con:
        rows = con.execute(
            """
            SELECT id, address, timestamp, scores
            FROM report_history
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "id": row[0],
                "address": row[1],
                "timestamp": row[2],
                "scores": json.loads(row[3]),
            }
        )
    return result


def load_report(report_id: int, db: str = _DEFAULT_DB) -> Optional[dict]:
    """Load the full report (including markdown) by id."""
    _ensure_table(db)
    with _conn(db) as con:
        row = con.execute(
            """
            SELECT id, address, timestamp, report_markdown, tool_results, scores,
                   purchase_price, hoa_fees
            FROM report_history
            WHERE id = ?
            """,
            (report_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "address": row[1],
        "timestamp": row[2],
        "report_markdown": row[3],
        "tool_results": json.loads(row[4]),
        "scores": json.loads(row[5]),
        "purchase_price": row[6],
        "hoa_fees": row[7],
    }


def delete_report(report_id: int, db: str = _DEFAULT_DB) -> None:
    """Delete a single report row."""
    _ensure_table(db)
    with _conn(db) as con:
        con.execute("DELETE FROM report_history WHERE id = ?", (report_id,))


def clear_history(db: str = _DEFAULT_DB) -> None:
    """Remove all history rows."""
    _ensure_table(db)
    with _conn(db) as con:
        con.execute("DELETE FROM report_history")
