from __future__ import annotations

import sqlite3
import json
from typing import Any, Dict, Optional


def ensure_decision_log_table(conn: sqlite3.Connection) -> None:
    """
    Ensure the decision_logs table exists.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS decision_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        decision_type TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        decision_value TEXT,
        reason TEXT,
        context_json TEXT
    )
    """)


def log_decision(
    conn: sqlite3.Connection,
    decision_type: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    decision_value: Optional[str] = None,
    reason: str = "",
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Insert a decision log entry into SQLite.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active DB connection.
    decision_type : str
        Type of decision (e.g. 'financial_tier_refresh').
    entity_type : str
        Entity involved (e.g. 'patient', 'system').
    entity_id : str | None
        Optional ID of the entity.
    decision_value : str | None
        Result of the decision.
    reason : str
        Explanation of why the decision occurred.
    context : dict | None
        Additional structured metadata.
    """

    ensure_decision_log_table(conn)

    context_json = None
    if context is not None:
        try:
            context_json = json.dumps(context, ensure_ascii=False)
        except Exception:
            context_json = str(context)

    conn.execute(
        """
        INSERT INTO decision_logs (
            decision_type,
            entity_type,
            entity_id,
            decision_value,
            reason,
            context_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            decision_type,
            entity_type,
            entity_id,
            decision_value,
            reason,
            context_json
        )
    )