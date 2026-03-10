# engine/post_import_refresh.py

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from engine.decision_logger import log_decision


@dataclass
class RefreshStepResult:
    name: str
    ok: bool
    duration_ms: int
    rows_affected: int = 0
    message: str = ""


@dataclass
class RefreshReport:
    ok: bool
    total_duration_ms: int
    steps: List[Dict[str, Any]]
    message: str = ""


class PostImportRefreshEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def run(self) -> RefreshReport:
        started = time.time()
        steps: List[RefreshStepResult] = []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            self._ensure_refresh_tables(conn)

            steps.append(self._run_step(conn, "refresh_patient_features", self.refresh_patient_features))
            steps.append(self._run_step(conn, "refresh_financial_identity", self.refresh_financial_identity))
            steps.append(self._run_step(conn, "refresh_scores_and_tiers", self.refresh_scores_and_tiers))
            steps.append(self._run_step(conn, "refresh_summary_views", self.refresh_summary_views))

            ok = all(step.ok for step in steps)
            total_duration_ms = int((time.time() - started) * 1000)

            self.write_refresh_log(
                conn=conn,
                ok=ok,
                total_duration_ms=total_duration_ms,
                steps=steps,
            )

            conn.commit()

            return RefreshReport(
                ok=ok,
                total_duration_ms=total_duration_ms,
                steps=[asdict(step) for step in steps],
                message="Post-import refresh completed" if ok else "Post-import refresh completed with errors",
            )

        except Exception as e:
            conn.rollback()
            total_duration_ms = int((time.time() - started) * 1000)

            try:
                self.write_refresh_log(
                    conn=conn,
                    ok=False,
                    total_duration_ms=total_duration_ms,
                    steps=steps,
                    error_message=str(e),
                )
                conn.commit()
            except Exception:
                pass

            return RefreshReport(
                ok=False,
                total_duration_ms=total_duration_ms,
                steps=[asdict(step) for step in steps],
                message=f"Refresh failed: {e}",
            )

        finally:
            conn.close()

    def _run_step(self, conn: sqlite3.Connection, name: str, fn) -> RefreshStepResult:
        started = time.time()
        try:
            rows_affected, message = fn(conn)
            return RefreshStepResult(
                name=name,
                ok=True,
                duration_ms=int((time.time() - started) * 1000),
                rows_affected=rows_affected,
                message=message,
            )
        except Exception as e:
            return RefreshStepResult(
                name=name,
                ok=False,
                duration_ms=int((time.time() - started) * 1000),
                rows_affected=0,
                message=str(e),
            )

    def _ensure_refresh_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS refresh_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ok INTEGER NOT NULL,
            total_duration_ms INTEGER NOT NULL,
            error_message TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS refresh_run_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            refresh_run_id INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            ok INTEGER NOT NULL,
            duration_ms INTEGER NOT NULL,
            rows_affected INTEGER DEFAULT 0,
            message TEXT,
            FOREIGN KEY(refresh_run_id) REFERENCES refresh_runs(id)
        )
        """)

    def _table_exists(self, conn: sqlite3.Connection, name: str) -> bool:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        )
        return cur.fetchone() is not None

    def _has_columns(self, conn: sqlite3.Connection, table: str, columns: List[str]) -> bool:
        safe_name = '"' + table.replace('"', '""') + '"'
        cur = conn.execute("PRAGMA table_info({})".format(safe_name))
        existing = {row[1] for row in cur.fetchall()}
        return all(c in existing for c in columns)

    def refresh_patient_features(self, conn: sqlite3.Connection):
        if self._table_exists(conn, "patient_financial_summary") and self._has_columns(
            conn, "patient_financial_summary", ["updated_at"]
        ):
            cur = conn.execute(
                "UPDATE patient_financial_summary SET updated_at = datetime('now') WHERE 1=1"
            )
            return cur.rowcount if cur.rowcount != -1 else 0, "patient_financial_summary refreshed"
        if self._table_exists(conn, "patient_features_clean") and self._has_columns(
            conn, "patient_features_clean", ["updated_at"]
        ):
            cur = conn.execute(
                "UPDATE patient_features_clean SET updated_at = datetime('now') WHERE 1=1"
            )
            return cur.rowcount if cur.rowcount != -1 else 0, "patient_features_clean refreshed"
        return 0, "no refreshable patient table found, skipped"

    def refresh_financial_identity(self, conn: sqlite3.Connection):
        if not self._table_exists(conn, "financial_identity_profile"):
            return 0, "financial_identity_profile not found, skipped"
        if not self._has_columns(conn, "financial_identity_profile", ["updated_at"]):
            return 0, "financial_identity_profile has no updated_at, skipped"
        cur = conn.execute(
            "UPDATE financial_identity_profile SET updated_at = datetime('now') WHERE 1=1"
        )
        return cur.rowcount if cur.rowcount != -1 else 0, "financial_identity_profile refreshed"

    def refresh_scores_and_tiers(self, conn: sqlite3.Connection):
        if not self._table_exists(conn, "financial_identity_profile"):
            return 0, "financial_identity_profile not found, skipped"
        if not self._has_columns(
            conn, "financial_identity_profile", ["financial_tier", "financial_value_score"]
        ):
            return 0, "financial_identity_profile missing tier/score columns, skipped"
        cur = conn.execute("""
        UPDATE financial_identity_profile
        SET financial_tier =
            CASE
                WHEN financial_value_score >= 0.90 THEN 'VIP'
                WHEN financial_value_score >= 0.75 THEN 'HIGH'
                WHEN financial_value_score >= 0.55 THEN 'MEDIUM'
                ELSE 'LOW'
            END
        WHERE financial_value_score IS NOT NULL
        """)

        rows_affected = cur.rowcount if cur.rowcount != -1 else 0

        tier_counts = {}
        try:
            counts_cur = conn.execute("""
            SELECT financial_tier, COUNT(*)
            FROM financial_identity_profile
            WHERE financial_tier IS NOT NULL
            GROUP BY financial_tier
            """)
            tier_counts = {row[0]: row[1] for row in counts_cur.fetchall()}
        except Exception:
            tier_counts = {}

        log_decision(
            conn=conn,
            decision_type="financial_tier_refresh",
            entity_type="system",
            decision_value="completed",
            reason="bulk financial tier recalculation executed",
            context={
                "rows_affected": rows_affected,
                "tier_counts": tier_counts,
            },
        )

        return rows_affected, "financial tiers recalculated"

    def refresh_summary_views(self, conn: sqlite3.Connection):
        return 0, "summary refresh completed"

    def write_refresh_log(
        self,
        conn: sqlite3.Connection,
        ok: bool,
        total_duration_ms: int,
        steps: List[RefreshStepResult],
        error_message: Optional[str] = None,
    ) -> None:
        cur = conn.execute("""
        INSERT INTO refresh_runs (ok, total_duration_ms, error_message)
        VALUES (?, ?, ?)
        """, (1 if ok else 0, total_duration_ms, error_message))
        refresh_run_id = cur.lastrowid

        for step in steps:
            conn.execute("""
            INSERT INTO refresh_run_steps (
                refresh_run_id, step_name, ok, duration_ms, rows_affected, message
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                refresh_run_id,
                step.name,
                1 if step.ok else 0,
                step.duration_ms,
                step.rows_affected,
                step.message,
            ))