# -*- coding: utf-8 -*-
"""
Build patient_insurance_profile from payments_unified_staging.insurer_raw.

Aggregates per crm_patient_code (record_no):
- most_frequent_insurer: mode of normalized insurer
- most_recent_insurer: normalized insurer from row with latest appointment_date_raw (then id)
- distinct_insurers_count: count of distinct normalized insurers

Uses app.financial.interpretation.normalize_insurer for normalization (removes % and (n) suffixes).
Does NOT modify payments_unified_staging.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.financial.interpretation import normalize_insurer

DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    str(REPO / "atieh_clinic_recovery81_test.db")
    if (REPO / "atieh_clinic_recovery81_test.db").exists()
    else str(REPO / "atieh_clinic_working.db")
    if (REPO / "atieh_clinic_working.db").exists()
    else str(REPO / "atieh_clinic.db")
)

STAGING_TABLE = "payments_unified_staging"
PROFILE_TABLE = "patient_insurance_profile"


def run_schema(conn: sqlite3.Connection) -> None:
    path = REPO / "sql" / "patient_insurance_profile_schema.sql"
    if path.exists():
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _most_recent_insurer(rows: list[tuple[str | None, str | None, int]]) -> str | None:
    """Rows: (insurer_raw, appointment_date_raw, id). Return normalized insurer from row with latest date then id."""
    if not rows:
        return None
    # Sort: appointment_date_raw DESC (nulls last), id DESC
    sorted_rows = sorted(
        rows,
        key=lambda r: (r[1] or "", r[2]),
        reverse=True,
    )
    raw = sorted_rows[0][0]
    return normalize_insurer(raw) if raw else None


def _most_frequent_insurer(normalized_list: list[str]) -> str | None:
    """Return mode of non-empty normalized insurers."""
    non_empty = [s for s in normalized_list if s and s.strip()]
    if not non_empty:
        return None
    return Counter(non_empty).most_common(1)[0][0]


def main() -> None:
    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    run_schema(conn)

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT record_no, insurer_raw, appointment_date_raw, id
        FROM {STAGING_TABLE}
        WHERE record_no IS NOT NULL AND TRIM(record_no) != ''
        """
    )
    rows = cur.fetchall()

    # Group by record_no
    by_code: dict[str, list[tuple[str | None, str | None, int]]] = {}
    for record_no, insurer_raw, appointment_date_raw, row_id in rows:
        code = (record_no or "").strip()
        if not code:
            continue
        if code not in by_code:
            by_code[code] = []
        by_code[code].append((insurer_raw, appointment_date_raw, row_id))

    conn.execute(f"DELETE FROM {PROFILE_TABLE}")
    inserted = 0
    for crm_code, group_rows in by_code.items():
        normalized_all = [normalize_insurer(r[0]) for r in group_rows]
        normalized_non_empty = [s for s in normalized_all if s and s.strip()]
        distinct_count = len(set(normalized_non_empty))
        most_frequent = _most_frequent_insurer(normalized_all)
        most_recent = _most_recent_insurer(group_rows)
        conn.execute(
            f"""
            INSERT INTO {PROFILE_TABLE}
            (crm_patient_code, most_frequent_insurer, most_recent_insurer, distinct_insurers_count, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (crm_code, most_frequent, most_recent, distinct_count),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Built {PROFILE_TABLE}: {inserted:,} rows from {STAGING_TABLE}")


if __name__ == "__main__":
    main()
