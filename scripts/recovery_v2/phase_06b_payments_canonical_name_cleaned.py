# -*- coding: utf-8 -*-
import re
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db")

GENERIC_NAMES = {"", "nan", "دندانپزشکی"}

def clean_payment_name(name: str):
    if not name:
        return ""
    s = str(name).strip()
    s = re.sub(r"^\d+\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def canonical_name(name: str):
    if not name:
        return ""
    parts = [p.strip() for p in str(name).split() if p.strip()]
    parts = sorted(parts)
    return " ".join(parts)

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else 0

def main():
    print(f"DB_PATH = {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Phase 06B - Payments Canonical Name Cleaned ===\n")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source = 'payments_canonical'
    """)

    cur.execute("DROP TABLE IF EXISTS tmp_unrecovered_patient_canon")
    cur.execute("DROP TABLE IF EXISTS tmp_payments_canon")
    cur.execute("DROP TABLE IF EXISTS tmp_unrecovered_patient_canon_stats")
    cur.execute("DROP TABLE IF EXISTS tmp_payments_canon_stats")

    cur.execute("""
        CREATE TABLE tmp_unrecovered_patient_canon (
            patient_id INTEGER NOT NULL,
            canon_name TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE tmp_payments_canon (
            payment_id INTEGER NOT NULL,
            payment_phone_norm TEXT,
            phone_type TEXT,
            canon_name TEXT NOT NULL
        )
    """)

    # unrecovered patients only
    patient_rows = cur.execute("""
        SELECT pl.patient_id, pl.patient_name_norm
        FROM patient_lookup_norm pl
        WHERE (pl.patient_phone_norm IS NULL OR TRIM(pl.patient_phone_norm) = '')
          AND pl.patient_name_norm IS NOT NULL
          AND TRIM(pl.patient_name_norm) <> ''
          AND pl.patient_id NOT IN (
              SELECT DISTINCT patient_id
              FROM patient_identity_evidence_v2
          )
    """).fetchall()

    patient_data = []
    for patient_id, patient_name_norm in patient_rows:
        if patient_name_norm in GENERIC_NAMES:
            continue
        cname = canonical_name(patient_name_norm)
        if not cname or cname in GENERIC_NAMES:
            continue
        patient_data.append((patient_id, cname))

    cur.executemany("""
        INSERT INTO tmp_unrecovered_patient_canon (patient_id, canon_name)
        VALUES (?, ?)
    """, patient_data)

    payment_rows = cur.execute("""
        SELECT payment_id, payment_name_norm, payment_phone_norm, phone_type
        FROM payments_lookup_norm
        WHERE payment_name_norm IS NOT NULL
          AND TRIM(payment_name_norm) <> ''
    """).fetchall()

    payment_data = []
    for payment_id, payment_name_norm, payment_phone_norm, phone_type in payment_rows:
        cleaned = clean_payment_name(payment_name_norm)
        if not cleaned or cleaned in GENERIC_NAMES:
            continue
        cname = canonical_name(cleaned)
        if not cname or cname in GENERIC_NAMES:
            continue
        payment_data.append((payment_id, payment_phone_norm, phone_type, cname))

    cur.executemany("""
        INSERT INTO tmp_payments_canon (payment_id, payment_phone_norm, phone_type, canon_name)
        VALUES (?, ?, ?, ?)
    """, payment_data)

    conn.commit()

    cur.execute("""
        CREATE TABLE tmp_unrecovered_patient_canon_stats AS
        SELECT canon_name, COUNT(*) AS cnt
        FROM tmp_unrecovered_patient_canon
        GROUP BY canon_name
    """)

    cur.execute("""
        CREATE TABLE tmp_payments_canon_stats AS
        SELECT canon_name, COUNT(*) AS cnt
        FROM tmp_payments_canon
        GROUP BY canon_name
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_upc_name ON tmp_unrecovered_patient_canon(canon_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_pc_name ON tmp_payments_canon(canon_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_upc_stats_name ON tmp_unrecovered_patient_canon_stats(canon_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_pc_stats_name ON tmp_payments_canon_stats(canon_name)")
    conn.commit()

    now_ts = datetime.now().isoformat(timespec="seconds")

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
            END AS candidate_mobile,
            CASE
                WHEN pay.phone_type = 'landline' OR pay.phone_type IS NULL THEN pay.payment_phone_norm
                ELSE NULL
            END AS candidate_landline,
            'payments_canonical' AS source,
            'canonical_name_cleaned' AS evidence_type,
            0.89 AS confidence,
            1 AS match_rank,
            ? AS created_at
        FROM tmp_unrecovered_patient_canon p
        JOIN tmp_unrecovered_patient_canon_stats ps
          ON ps.canon_name = p.canon_name
        JOIN tmp_payments_canon_stats pms
          ON pms.canon_name = p.canon_name
        JOIN tmp_payments_canon pay
          ON pay.canon_name = p.canon_name
        WHERE ps.cnt <= 2
          AND pms.cnt <= 2
    """, (now_ts,))
    inserted = cur.rowcount
    conn.commit()

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")
    payments_matched = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'payments_canonical'
    """)
    union_patients = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
    """)
    union_coverage = round((union_patients * 100.0 / total_patients), 2) if total_patients else 0.0

    print(f"payments canonical inserted : {inserted:,}")
    print(f"payments matched patients   : {payments_matched:,}")
    print(f"union patients             : {union_patients:,}")
    print(f"union coverage             : {union_coverage:.2f}%")

    conn.close()

if __name__ == "__main__":
    main()
