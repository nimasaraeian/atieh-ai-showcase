# -*- coding: utf-8 -*-
"""
Phone Recovery Preparation.
- Audit patients.phone
- Fill patients_phone_normalized, payments_phone_normalized
- Build payments_phone_patient_match (single | collision | no_match)
- Output stats; do NOT update final patient_id.
"""
from __future__ import annotations

import re
import sys
import os
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql"
BATCH = 5000


def _normalize_digits(s: str) -> str:
    """Persian/Arabic digits to English; then digits only."""
    persian = "۰۱۲۳۴۵۶۷۸۹"
    arabic = "٠١٢٣٤٥٦٧٨٩"
    t = str(s)
    for i, p in enumerate(persian):
        t = t.replace(p, str(i))
    for i, a in enumerate(arabic):
        t = t.replace(a, str(i))
    return "".join(c for c in t if c.isdigit())


def normalize_phone_to_09(raw: str | None) -> str | None:
    """
    Normalize to 09xxxxxxxxx (11 digits) or None.
    Handles: 9xxxxxxxxx, 09xxxxxxxxx, 98xxxxxxxxxx, +98xxxxxxxxxx, multiple numbers (first valid).
    """
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip()
    digits = _normalize_digits(s)
    if not digits:
        return None
    # Split on separators and take first valid 09 mobile
    for part in re.split(r"[;\s,/\|]+", s):
        d = _normalize_digits(part)
        if d.startswith("98") and len(d) >= 12:
            d = "0" + d[2:]
        if len(d) == 10 and d.startswith("9"):
            d = "0" + d
        if len(d) == 11 and d.startswith("09"):
            return d
    # Single block
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("09"):
        return digits
    return None


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

    schema_path = SQL_DIR / "phone_recovery_prep_schema.sql"
    if schema_path.exists():
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.commit()

    cur = conn.cursor()

    # ─── 1) Audit patients.phone ────────────────────────────────────────────
    cur.execute("SELECT id, phone FROM patients")
    patients = cur.fetchall()
    total_patients = len(patients)
    filled = sum(1 for r in patients if r["phone"] is not None and str(r["phone"]).strip())
    patient_norms = []
    valid_patient_phones = 0
    samples_raw = []
    for r in patients:
        raw = r["phone"]
        if raw is not None and str(raw).strip():
            if len(samples_raw) < 8:
                samples_raw.append(str(raw).strip())
        norm = normalize_phone_to_09(raw)
        if norm:
            valid_patient_phones += 1
        patient_norms.append((r["id"], raw, norm, 1 if norm else 0))

    print("--- Audit: patients.phone ---")
    print(f"  Total patients:     {total_patients}")
    print(f"  Phone filled:       {filled}")
    print(f"  Valid (09xxxxxxxxx): {valid_patient_phones}")
    print("  Sample raw:         " + ", ".join(repr(s) for s in samples_raw[:5]))
    print()

    # ─── 2) Fill patients_phone_normalized ───────────────────────────────────
    cur.execute("DELETE FROM patients_phone_normalized")
    conn.commit()
    cur.executemany(
        """INSERT INTO patients_phone_normalized (patient_id, phone_raw, phone_norm, is_valid)
           VALUES (?, ?, ?, ?)""",
        patient_norms,
    )
    conn.commit()
    print(f"Filled patients_phone_normalized: {len(patient_norms)} rows")

    # ─── 3) Fill payments_phone_normalized from payments_unified_staging.phone_raw ───
    cur.execute("SELECT id, phone_raw FROM payments_unified_staging")
    staging_rows = cur.fetchall()
    pay_norms = []
    for r in staging_rows:
        raw = r["phone_raw"]
        norm = normalize_phone_to_09(raw)
        pay_norms.append((r["id"], raw, norm, 1 if norm else 0))
    cur.execute("DELETE FROM payments_phone_normalized")
    conn.commit()
    cur.executemany(
        """INSERT INTO payments_phone_normalized (staging_id, phone_raw, phone_norm, is_valid)
           VALUES (?, ?, ?, ?)""",
        pay_norms,
    )
    conn.commit()
    valid_payment_phones = sum(1 for _, _, n, v in pay_norms if v)
    print(f"Filled payments_phone_normalized: {len(pay_norms)} rows (valid: {valid_payment_phones})")

    # ─── 4) Build phone_norm -> patient_id(s) lookup ─────────────────────────
    phone_to_patients = defaultdict(list)
    for pid, _, norm, valid in patient_norms:
        if valid and norm:
            phone_to_patients[norm].append(pid)

    # ─── 5) Fill payments_phone_patient_match ──────────────────────────────
    cur.execute("DELETE FROM payments_phone_patient_match")
    conn.commit()
    match_rows = []
    for staging_id, _, norm, is_valid in pay_norms:
        if not is_valid or not norm:
            match_rows.append((staging_id, norm or "", None, "no_match"))
        else:
            pids = phone_to_patients.get(norm, [])
            if len(pids) == 0:
                match_rows.append((staging_id, norm, None, "no_match"))
            elif len(pids) == 1:
                match_rows.append((staging_id, norm, pids[0], "single"))
            else:
                match_rows.append((staging_id, norm, None, "collision"))
        if len(match_rows) >= BATCH:
            cur.executemany(
                """INSERT INTO payments_phone_patient_match (staging_id, phone_norm, patient_id, match_status)
                   VALUES (?, ?, ?, ?)""",
                match_rows,
            )
            conn.commit()
            match_rows.clear()
    if match_rows:
        cur.executemany(
            """INSERT INTO payments_phone_patient_match (staging_id, phone_norm, patient_id, match_status)
               VALUES (?, ?, ?, ?)""",
            match_rows,
        )
        conn.commit()
    print("Filled payments_phone_patient_match")

    # ─── 6) Stats ───────────────────────────────────────────────────────────
    total_staging = cur.execute("SELECT COUNT(*) FROM payments_unified_staging").fetchone()[0]
    single = cur.execute("SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'single'").fetchone()[0]
    collision = cur.execute("SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'collision'").fetchone()[0]
    no_match = cur.execute("SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'no_match'").fetchone()[0]
    unique_patients = cur.execute(
        "SELECT COUNT(DISTINCT patient_id) FROM payments_phone_patient_match WHERE match_status = 'single' AND patient_id IS NOT NULL"
    ).fetchone()[0]
    coverage_gained = single

    print()
    print("--- Phone Recovery Prep Stats ---")
    print(f"  Total staging rows:              {total_staging}")
    print(f"  Valid normalized payment phones: {valid_payment_phones}")
    print(f"  Valid normalized patient phones: {valid_patient_phones}")
    print(f"  Single matches:                  {single}")
    print(f"  Unique patients matched:        {unique_patients}")
    print(f"  Collisions:                      {collision}")
    print(f"  No match:                        {no_match}")
    print(f"  Coverage gained by phone:        {coverage_gained} rows")
    print()

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
