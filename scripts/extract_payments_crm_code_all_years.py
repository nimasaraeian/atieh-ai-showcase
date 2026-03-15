# -*- coding: utf-8 -*-
"""
Extract CRM code from patient_name_raw for ALL years in payments_unified_staging.
- Regex: digits inside final parentheses.
- Clean name: remove parentheses block, normalize Persian/Arabic.
- Compare extracted code to record_no; set extracted_code_equals_record_no_flag.
- Writes only to payments_crm_code_all_years (does not modify staging).
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.helpers.persian_text_normalization import (
    normalize_persian_text,
    digits_persian_arabic_to_english,
    record_no_norm,
)

# Digits in final parentheses: e.g. "محمودي معصومه(101674)" -> 101674
CRM_FINAL_PAREN = re.compile(r"\((\d+)\)\s*$")


def extract_crm_code_from_final_parens(patient_name_raw: str | None) -> str | None:
    """Extract numeric code from final parentheses. Returns None if no match."""
    if not patient_name_raw or not isinstance(patient_name_raw, str):
        return None
    s = patient_name_raw.strip()
    m = CRM_FINAL_PAREN.search(s)
    return m.group(1) if m else None


def clean_patient_name_remove_parens(patient_name_raw: str | None) -> str:
    """Remove final (digits) from name and normalize Persian/Arabic."""
    if not patient_name_raw or not isinstance(patient_name_raw, str):
        return ""
    s = patient_name_raw.strip()
    s = re.sub(r"\s*\(\d+\)\s*$", "", s).strip()
    return normalize_persian_text(s) if s else ""


def run_schema(conn: sqlite3.Connection) -> None:
    schema_path = REPO / "sql" / "payments_crm_code_all_years_schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    conn.executescript(schema_path.read_text(encoding="utf-8"))


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    run_schema(conn)

    conn.execute("DELETE FROM payments_crm_code_all_years")
    conn.commit()

    cur = conn.execute(
        """
        SELECT id, source_file, shamsi_year, patient_name_raw, record_no
        FROM payments_unified_staging
        ORDER BY id
        """
    )
    rows = cur.fetchall()
    total = len(rows)
    print(f"Processing {total:,} rows from payments_unified_staging...")

    insert_sql = """
        INSERT INTO payments_crm_code_all_years (
            payment_row_id, source_file, shamsi_year, patient_name_raw, patient_name_clean,
            extracted_crm_code, record_no, extracted_code_equals_record_no_flag, parse_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    batch = []
    batch_size = 5000
    for (row_id, source_file, shamsi_year, patient_name_raw, record_no) in rows:
        raw = patient_name_raw if patient_name_raw else ""
        extracted = extract_crm_code_from_final_parens(raw)
        clean = clean_patient_name_remove_parens(raw)

        if extracted is None:
            parse_status = "no_code"
            equals_flag = 0
        else:
            parse_status = "ok"
            rec_norm = record_no_norm(record_no)
            ext_norm = record_no_norm(extracted)
            equals_flag = 1 if (rec_norm is not None and ext_norm is not None and rec_norm == ext_norm) else 0

        batch.append((
            row_id, source_file, shamsi_year, patient_name_raw or None, clean or None,
            extracted, record_no, equals_flag, parse_status,
        ))
        if len(batch) >= batch_size:
            conn.executemany(insert_sql, batch)
            conn.commit()
            batch = []

    if batch:
        conn.executemany(insert_sql, batch)
        conn.commit()

    inserted = conn.execute("SELECT COUNT(*) FROM payments_crm_code_all_years").fetchone()[0]
    with_code = conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok'"
    ).fetchone()[0]
    equals = conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE extracted_code_equals_record_no_flag = 1"
    ).fetchone()[0]
    print(f"Inserted {inserted:,} rows. With extracted code: {with_code:,}. Code == record_no: {equals:,}")
    conn.close()


if __name__ == "__main__":
    main()
