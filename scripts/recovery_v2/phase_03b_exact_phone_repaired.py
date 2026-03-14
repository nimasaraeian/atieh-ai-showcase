# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db")

def normalize_digits(raw):
    if raw is None:
        return ""
    return "".join(ch for ch in str(raw) if ch.isdigit())

def repair_phone_variants(digits: str):
    if not digits:
        return []
    d = normalize_digits(digits)
    out = []
    if d:
        out.append(d)
    if len(d) == 10 and d.startswith("9"):
        v = "0" + d
        if v not in out:
            out.append(v)
    return out

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else 0

def ensure_tables(cur):
    cur.execute("DROP TABLE IF EXISTS tmp_patient_phone_variants")
    cur.execute("DROP TABLE IF EXISTS tmp_payment_phone_variants")
    cur.execute("DROP TABLE IF EXISTS tmp_appointment_phone_variants")

    cur.execute("""
        CREATE TABLE tmp_patient_phone_variants (
            patient_id INTEGER NOT NULL,
            variant_phone TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE tmp_payment_phone_variants (
            payment_id INTEGER NOT NULL,
            payment_phone_norm TEXT,
            phone_type TEXT,
            variant_phone TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE tmp_appointment_phone_variants (
            arb_id INTEGER NOT NULL,
            appointment_phone_norm TEXT,
            variant_phone TEXT NOT NULL
        )
    """)

def build_patient_variants(cur):
    rows = cur.execute("""
        SELECT patient_id, patient_phone_norm
        FROM patient_lookup_norm
        WHERE patient_phone_norm IS NOT NULL
          AND TRIM(patient_phone_norm) <> ''
    """).fetchall()

    data = []
    seen = set()
    for patient_id, phone in rows:
        for v in repair_phone_variants(phone):
            key = (patient_id, v)
            if key not in seen:
                seen.add(key)
                data.append((patient_id, v))

    cur.executemany("""
        INSERT INTO tmp_patient_phone_variants (patient_id, variant_phone)
        VALUES (?, ?)
    """, data)

def build_payment_variants(cur):
    rows = cur.execute("""
        SELECT payment_id, payment_phone_norm, phone_type
        FROM payments_lookup_norm
        WHERE payment_phone_norm IS NOT NULL
          AND TRIM(payment_phone_norm) <> ''
    """).fetchall()

    data = []
    seen = set()
    for payment_id, phone_norm, phone_type in rows:
        for v in repair_phone_variants(phone_norm):
            key = (payment_id, phone_norm, phone_type, v)
            if key not in seen:
                seen.add(key)
                data.append((payment_id, phone_norm, phone_type, v))

    cur.executemany("""
        INSERT INTO tmp_payment_phone_variants (payment_id, payment_phone_norm, phone_type, variant_phone)
        VALUES (?, ?, ?, ?)
    """, data)

def build_appointment_variants(cur):
    rows = cur.execute("""
        SELECT arb_id, appointment_phone_norm
        FROM appointment_phone_helper
        WHERE appointment_phone_norm IS NOT NULL
          AND TRIM(appointment_phone_norm) <> ''
    """).fetchall()

    data = []
    seen = set()
    for arb_id, phone_norm in rows:
        for v in repair_phone_variants(phone_norm):
            key = (arb_id, phone_norm, v)
            if key not in seen:
                seen.add(key)
                data.append((arb_id, phone_norm, v))

    cur.executemany("""
        INSERT INTO tmp_appointment_phone_variants (arb_id, appointment_phone_norm, variant_phone)
        VALUES (?, ?, ?)
    """, data)

def main():
    print(f"DB_PATH = {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Recovery v2 / Phase 03B - Exact Phone Repaired ===\n")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source IN ('payments_repaired', 'appointment_bridge_repaired')
    """)
    conn.commit()

    ensure_tables(cur)
    build_patient_variants(cur)
    build_payment_variants(cur)
    build_appointment_variants(cur)
    conn.commit()

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_ppv_phone ON tmp_patient_phone_variants(variant_phone)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_payv_phone ON tmp_payment_phone_variants(variant_phone)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_apv_phone ON tmp_appointment_phone_variants(variant_phone)")
    conn.commit()

    now_1 = datetime.now().isoformat(timespec="seconds")

    cur.execute("""
        INSERT INTO patient_identity_evidence_v2
        (
            patient_id,
            candidate_mobile,
            candidate_landline,
            source,
            evidence_type,
            confidence,
            match_rank,
            created_at
        )
        SELECT DISTINCT
            p.patient_id,
            CASE
                WHEN pay.phone_type = 'mobile' THEN pay.payment_phone_norm
                ELSE NULL
            END,
            CASE
                WHEN pay.phone_type = 'landline' OR pay.phone_type IS NULL THEN pay.payment_phone_norm
                ELSE NULL
            END,
            'payments_repaired',
            'exact_phone_repaired',
            0.84,
            1,
            ?
        FROM tmp_patient_phone_variants p
        JOIN tmp_payment_phone_variants pay
          ON p.variant_phone = pay.variant_phone
    """, (now_1,))
    payments_inserted = cur.rowcount
    conn.commit()

    now_2 = datetime.now().isoformat(timespec="seconds")

    cur.execute("""
        INSERT INTO patient_identity_evidence_v2
        (
            patient_id,
            candidate_mobile,
            candidate_landline,
            source,
            evidence_type,
            confidence,
            match_rank,
            created_at
        )
        SELECT DISTINCT
            p.patient_id,
            ap.appointment_phone_norm,
            NULL,
            'appointment_bridge_repaired',
            'exact_phone_repaired',
            0.86,
            1,
            ?
        FROM tmp_patient_phone_variants p
        JOIN tmp_appointment_phone_variants ap
          ON p.variant_phone = ap.variant_phone
    """, (now_2,))
    appt_inserted = cur.rowcount
    conn.commit()

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")
    matched = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source IN ('payments_repaired', 'appointment_bridge_repaired')
    """)
    coverage = round((matched * 100.0 / total_patients), 2) if total_patients else 0.0

    print(f"payments repaired inserted   : {payments_inserted:,}")
    print(f"appointment repaired inserted: {appt_inserted:,}")
    print(f"matched patients            : {matched:,}")
    print(f"coverage                    : {coverage:.2f}%")

    cur.execute("DROP TABLE IF EXISTS tmp_patient_phone_variants")
    cur.execute("DROP TABLE IF EXISTS tmp_payment_phone_variants")
    cur.execute("DROP TABLE IF EXISTS tmp_appointment_phone_variants")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
