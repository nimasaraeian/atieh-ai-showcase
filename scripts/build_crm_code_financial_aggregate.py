# -*- coding: utf-8 -*-
"""
Build crm_code_financial_aggregate from payments_crm_code_all_years + payments_unified_staging.
- Joins to staging for net_received_raw.
- Safely parses numeric values (Persian/Arabic digits, commas).
- Aggregates by crm_patient_code: count, total/positive/negative sums, year range, canonical name.
- Does not modify source tables.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.helpers.persian_text_normalization import digits_persian_arabic_to_english


def parse_net_received_raw(raw: str | None) -> float | None:
    """Parse net_received_raw to float. Handles Persian/Arabic digits and commas. Returns None on failure."""
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = digits_persian_arabic_to_english(s)
    s = s.replace(",", "").replace(" ", "")
    # Optional leading minus
    sign = 1
    if s.startswith("-"):
        sign = -1
        s = s[1:]
    s = "".join(c for c in s if c.isdigit() or c == ".")
    if not s:
        return None
    try:
        return sign * float(s)
    except ValueError:
        return None


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    # Ensure aggregate table exists
    schema_path = REPO / "sql" / "payments_crm_code_all_years_schema.sql"
    if schema_path.exists():
        conn.executescript(schema_path.read_text(encoding="utf-8"))

    conn.execute("DELETE FROM crm_code_financial_aggregate")
    conn.commit()

    cur = conn.execute(
        """
        SELECT c.payment_row_id, c.extracted_crm_code, c.shamsi_year, c.patient_name_clean,
               s.net_received_raw
        FROM payments_crm_code_all_years c
        JOIN payments_unified_staging s ON s.id = c.payment_row_id
        WHERE c.parse_status = 'ok' AND c.extracted_crm_code IS NOT NULL AND TRIM(c.extracted_crm_code) <> ''
        """
    )
    rows = cur.fetchall()

    # Aggregate by crm_patient_code
    by_code: dict[str, dict] = defaultdict(lambda: {
        "years": set(),
        "total_net": 0.0,
        "positive_sum": 0.0,
        "negative_sum": 0.0,
        "count": 0,
        "name_counts": defaultdict(int),
    })
    for (payment_row_id, crm_code, shamsi_year, patient_name_clean, net_received_raw) in rows:
        code = (crm_code or "").strip()
        if not code:
            continue
        by_code[code]["years"].add(shamsi_year)
        by_code[code]["count"] += 1
        name = (patient_name_clean or "").strip() or "(blank)"
        by_code[code]["name_counts"][name] += 1
        val = parse_net_received_raw(net_received_raw)
        if val is not None:
            by_code[code]["total_net"] += val
            if val >= 0:
                by_code[code]["positive_sum"] += val
            else:
                by_code[code]["negative_sum"] += val

    insert_sql = """
        INSERT INTO crm_code_financial_aggregate (
            crm_patient_code, first_year, last_year, payment_rows_count,
            total_net_received, positive_net_received_sum, negative_net_received_sum,
            distinct_patient_names_count, canonical_patient_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for code, data in by_code.items():
        years = data["years"]
        first_year = min(years)
        last_year = max(years)
        name_counts = data["name_counts"]
        canonical = max(name_counts, key=name_counts.get) if name_counts else None
        if canonical == "(blank)":
            canonical = None
        conn.execute(insert_sql, (
            code,
            first_year,
            last_year,
            data["count"],
            data["total_net"],
            data["positive_sum"],
            data["negative_sum"],
            len(name_counts),
            canonical,
        ))
    conn.commit()

    n = conn.execute("SELECT COUNT(*) FROM crm_code_financial_aggregate").fetchone()[0]
    print(f"Built crm_code_financial_aggregate: {n:,} distinct crm_patient_codes")
    conn.close()


if __name__ == "__main__":
    main()
