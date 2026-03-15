# -*- coding: utf-8 -*-
"""
Normalize identity fields from payments_unified_staging, appointments_unified_staging,
and patients into identity_normalized_* tables.
Idempotent: truncate normalized tables then repopulate.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"
sys.path.insert(0, str(REPO))

from scripts.helpers.persian_text_normalization import (
    patient_name_norm,
    patient_name_key,
    national_id_norm,
    record_no_norm as _record_no_norm_helper,
    digits_persian_arabic_to_english,
)
from scripts.helpers.phone_normalization import normalize_phone_primary_and_all


def record_no_norm(raw) -> str | None:
    """Record no: trim, digits only for matching; empty -> None."""
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = digits_persian_arabic_to_english(s)
    s = "".join(c for c in s if c.isdigit())
    return s if s else None


def date_norm_raw(raw) -> str | None:
    """Preserve raw; optional comparable string (minimal: keep as-is)."""
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return None
    s = str(raw).strip()
    return s if s else None


def run_schema(conn) -> None:
    for name in ("001_identity_resolution_schema.sql", "002_identity_resolution_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def normalize_payments(conn) -> int:
    conn.execute("DELETE FROM identity_normalized_payments")
    conn.commit()
    cur = conn.execute("""
        SELECT id, source_file, shamsi_year, patient_name_raw, phone_raw,
               national_id_raw, record_no, appointment_date_raw, net_received_raw
        FROM payments_unified_staging
    """)
    rows = cur.fetchall()
    ins = """
        INSERT INTO identity_normalized_payments (
            payments_staging_id, source_file, shamsi_year, patient_name_raw,
            patient_name_norm, patient_name_key, mobile_raw, mobile_primary_norm, mobile_all_norm_json,
            national_id_raw, national_id_norm, record_no_raw, record_no_norm,
            admission_date_raw, admission_date_norm, net_received_raw, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
    """
    count = 0
    for r in rows:
        (sid, src, year, name_raw, phone_raw, nid_raw, rec_raw, adm_raw, net_raw) = r
        name_n = patient_name_norm(name_raw)
        name_k = patient_name_key(name_raw)
        primary_phone, all_phones_json = normalize_phone_primary_and_all(phone_raw)
        nid_n = national_id_norm(nid_raw)
        rec_n = record_no_norm(rec_raw)
        adm_n = date_norm_raw(adm_raw)
        conn.execute(ins, (
            sid, src, year, name_raw, name_n, name_k, phone_raw, primary_phone, all_phones_json or "[]",
            nid_raw, nid_n, rec_raw, rec_n, adm_raw, adm_n, net_raw,
        ))
        count += 1
    conn.commit()
    return count


def normalize_appointments(conn) -> int:
    conn.execute("DELETE FROM identity_normalized_appointments")
    conn.commit()
    cur = conn.execute("""
        SELECT staging_id, source_file, shamsi_year, patient_name_combined_raw, patient_name_raw,
               phone_raw, record_no_raw, appointment_date_raw, doctor_name_raw
        FROM appointments_unified_staging
    """)
    rows = cur.fetchall()
    ins = """
        INSERT INTO identity_normalized_appointments (
            appointment_staging_id, source_file, shamsi_year, patient_name_raw,
            patient_name_norm, patient_name_key, phone_raw, phone_primary_norm, phone_all_norm_json,
            national_id_raw, national_id_norm, record_no_raw, record_no_norm,
            appointment_date_raw, appointment_date_norm, doctor_name_raw, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
    """
    count = 0
    for r in rows:
        (sid, src, year, name_combined, name_raw, phone_raw, rec_raw, date_raw, doctor_raw) = r
        name_use = name_combined or name_raw
        name_n = patient_name_norm(name_use)
        name_k = patient_name_key(name_use)
        primary_phone, all_phones_json = normalize_phone_primary_and_all(phone_raw)
        nid_n = None  # appointments typically have no national_id
        rec_n = record_no_norm(rec_raw)
        date_n = date_norm_raw(date_raw)
        conn.execute(ins, (
            sid, src, year, name_use, name_n, name_k, phone_raw, primary_phone, all_phones_json or "[]",
            None, nid_n, rec_raw, rec_n, date_raw, date_n, doctor_raw,
        ))
        count += 1
    conn.commit()
    return count


def normalize_patients(conn) -> int:
    conn.execute("DELETE FROM patients_identity_normalized")
    conn.commit()
    # patients table: id, name, phone, national_id (often empty)
    cur = conn.execute("SELECT id, name, phone, national_id FROM patients")
    rows = cur.fetchall()
    ins = """
        INSERT INTO patients_identity_normalized (
            patient_id, patient_name_raw, patient_name_norm, patient_name_key,
            phone_raw, phone_primary_norm, phone_all_norm_json,
            national_id_raw, national_id_norm, record_no_raw, record_no_norm, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
    """
    count = 0
    for r in rows:
        (pid, name_raw, phone_raw, nid_raw) = r
        name_n = patient_name_norm(name_raw)
        name_k = patient_name_key(name_raw)
        primary_phone, all_phones_json = normalize_phone_primary_and_all(phone_raw)
        nid_n = national_id_norm(nid_raw)
        conn.execute(ins, (
            pid, name_raw, name_n, name_k, phone_raw, primary_phone, all_phones_json or "[]",
            nid_raw, nid_n, None, None,
        ))
        count += 1
    conn.commit()
    return count


def main():
    import sqlite3

    db_path = os.environ.get("ATIEH_DB_PATH") or os.environ.get("DB_PATH") or str(REPO / "atieh_clinic_recovery81_test.db")
    db_path = Path(db_path)
    if not db_path.is_absolute():
        db_path = REPO / db_path
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA busy_timeout = 30000")
    run_schema(conn)

    print("Normalizing identity fields...")
    n_pay = normalize_payments(conn)
    print(f"  identity_normalized_payments: {n_pay} rows")
    n_app = normalize_appointments(conn)
    print(f"  identity_normalized_appointments: {n_app} rows")
    n_pt = normalize_patients(conn)
    print(f"  patients_identity_normalized: {n_pt} rows")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
