# -*- coding: utf-8 -*-
"""
National ID Recovery Preparation.
- جدول normalized را از national_id_raw پر می‌کند (فقط رقم، ۱۰ رقمی)
- با patients.national_id تطابق می‌زند
- خروجی در جدول میانی payments_national_id_patient_match ذخیره می‌شود (بدون update نهایی روی payments)
- آمارهای درخواستی را چاپ می‌کند
"""
from __future__ import annotations

import re
import sys
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql"
BATCH = 5000


def _norm_nid(s: str | None) -> str | None:
    """Extract digits only; return 10-char string or None."""
    if s is None or not str(s).strip():
        return None
    persian = "۰۱۲۳۴۵۶۷۸۹"
    t = str(s).strip()
    for i, p in enumerate(persian):
        t = t.replace(p, str(i))
    digits = re.sub(r"\D", "", t)
    if len(digits) != 10:
        return None
    return digits


def main():
    import sqlite3

    db_path = os.environ.get("ATIEH_DB_PATH") or os.environ.get("DB_PATH") or str(REPO / "atieh_clinic.db")
    db_path = Path(db_path)
    if not db_path.is_absolute():
        db_path = REPO / db_path
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")

    # Ensure schema
    schema_path = SQL_DIR / "unified_payments_staging_schema.sql"
    if schema_path.exists():
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.commit()

    cur = conn.cursor()

    # ─── 1) Fill payments_national_id_normalized ─────────────────────────────
    cur.execute("DELETE FROM payments_national_id_normalized")
    conn.commit()

    cur.execute("SELECT id, national_id_raw FROM payments_unified_staging")
    rows = cur.fetchall()
    norm_rows = []
    for r in rows:
        raw = r["national_id_raw"]
        nid_norm = _norm_nid(raw)
        is_valid = 1 if (nid_norm and len(nid_norm) == 10) else 0
        norm_rows.append((r["id"], raw, nid_norm, is_valid))

    cur.executemany(
        """INSERT INTO payments_national_id_normalized (staging_id, national_id_raw, national_id_norm, is_valid)
           VALUES (?, ?, ?, ?)""",
        norm_rows,
    )
    conn.commit()
    print(f"Filled payments_national_id_normalized: {len(norm_rows)} rows")

    # ─── 2) Build patient national_id lookup (normalized) ───────────────────
    cur.execute("SELECT id, national_id FROM patients WHERE national_id IS NOT NULL AND TRIM(national_id) <> ''")
    patient_nid = []
    for r in cur.fetchall():
        nid_norm = _norm_nid(r["national_id"])
        if nid_norm and len(nid_norm) == 10:
            patient_nid.append((nid_norm, r["id"]))
    # nid_norm -> list of patient_ids (for collision detection)
    from collections import defaultdict
    nid_to_patients = defaultdict(list)
    for nid, pid in patient_nid:
        nid_to_patients[nid].append(pid)

    # ─── 3) Fill payments_national_id_patient_match ────────────────────────
    cur.execute("DELETE FROM payments_national_id_patient_match")
    conn.commit()

    cur.execute("SELECT id, staging_id, national_id_norm, is_valid FROM payments_national_id_normalized")
    match_rows = []
    for r in cur.fetchall():
        staging_id = r["staging_id"]
        nid_norm = r["national_id_norm"]
        if not nid_norm or r["is_valid"] != 1:
            match_rows.append((staging_id, nid_norm or "", None, "no_match"))
            continue
        pids = nid_to_patients.get(nid_norm, [])
        if len(pids) == 0:
            match_rows.append((staging_id, nid_norm, None, "no_match"))
        elif len(pids) == 1:
            match_rows.append((staging_id, nid_norm, pids[0], "single"))
        else:
            match_rows.append((staging_id, nid_norm, None, "collision"))
        if len(match_rows) >= BATCH:
            cur.executemany(
                """INSERT INTO payments_national_id_patient_match (staging_id, national_id_norm, patient_id, match_status)
                   VALUES (?, ?, ?, ?)""",
                match_rows,
            )
            conn.commit()
            match_rows.clear()
    if match_rows:
        cur.executemany(
            """INSERT INTO payments_national_id_patient_match (staging_id, national_id_norm, patient_id, match_status)
               VALUES (?, ?, ?, ?)""",
            match_rows,
        )
        conn.commit()
    print("Filled payments_national_id_patient_match")

    # ─── 4) Stats ───────────────────────────────────────────────────────────
    total_staging = cur.execute("SELECT COUNT(*) FROM payments_unified_staging").fetchone()[0]
    nid_valid = cur.execute("SELECT COUNT(*) FROM payments_national_id_normalized WHERE is_valid = 1").fetchone()[0]
    match_single = cur.execute("SELECT COUNT(*) FROM payments_national_id_patient_match WHERE match_status = 'single'").fetchone()[0]
    match_collision = cur.execute("SELECT COUNT(*) FROM payments_national_id_patient_match WHERE match_status = 'collision'").fetchone()[0]
    match_no = cur.execute("SELECT COUNT(*) FROM payments_national_id_patient_match WHERE match_status = 'no_match'").fetchone()[0]
    unique_patient_match = cur.execute(
        "SELECT COUNT(DISTINCT patient_id) FROM payments_national_id_patient_match WHERE match_status = 'single' AND patient_id IS NOT NULL"
    ).fetchone()[0]
    coverage_gained = match_single  # rows that gained a patient_id via national_id

    print()
    print("─── National ID Recovery Prep Stats ───")
    print(f"  Total staging rows:           {total_staging}")
    print(f"  Valid national_id (10-digit): {nid_valid}")
    print(f"  Match with patients (single): {match_single}")
    print(f"  Unique patients matched:     {unique_patient_match}")
    print(f"  Collision (nid→multiple):    {match_collision}")
    print(f"  No match:                    {match_no}")
    print(f"  Coverage gained by NID:      {coverage_gained} rows")
    print()

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
