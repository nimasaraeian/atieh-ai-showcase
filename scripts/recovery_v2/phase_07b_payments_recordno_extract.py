# -*- coding: utf-8 -*-
import re
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db")

def extract_record_no(payment_name: str):
    if not payment_name:
        return None
    s = str(payment_name).strip()
    m = re.match(r"^(\d{3,})\b", s)
    if not m:
        return None
    return m.group(1)

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else 0

def main():
    print(f"DB_PATH = {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Phase 07B - Payments RecordNo Extract (Fixed Join) ===\n")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source = 'payments_recordno'
    """)

    cur.execute("DROP TABLE IF EXISTS tmp_payments_recordno")

    cur.execute("""
        CREATE TABLE tmp_payments_recordno (
            payment_id INTEGER NOT NULL,
            extracted_record_no TEXT,
            payment_phone_norm TEXT,
            phone_type TEXT,
            payment_name_norm TEXT
        )
    """)

    rows = cur.execute("""
        SELECT payment_id, payment_name_norm, payment_phone_norm, phone_type
        FROM payments_lookup_norm
        WHERE payment_name_norm IS NOT NULL
          AND TRIM(payment_name_norm) <> ''
    """).fetchall()

    data = []
    for payment_id, payment_name_norm, payment_phone_norm, phone_type in rows:
        rec = extract_record_no(payment_name_norm)
        if rec:
            data.append((payment_id, rec, payment_phone_norm, phone_type, payment_name_norm))

    cur.executemany("""
        INSERT INTO tmp_payments_recordno
        (payment_id, extracted_record_no, payment_phone_norm, phone_type, payment_name_norm)
        VALUES (?, ?, ?, ?, ?)
    """, data)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tmp_payrec_record_no ON tmp_payments_recordno(extracted_record_no)")
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
            rpm.patient_id,
            CASE
                WHEN tpr.phone_type = 'mobile' THEN tpr.payment_phone_norm
                ELSE NULL
            END AS candidate_mobile,
            CASE
                WHEN tpr.phone_type = 'landline' OR tpr.phone_type IS NULL THEN tpr.payment_phone_norm
                ELSE NULL
            END AS candidate_landline,
            'payments_recordno' AS source,
            'recordno_from_payment_name' AS evidence_type,
            0.94 AS confidence,
            1 AS match_rank,
            ? AS created_at
        FROM tmp_payments_recordno tpr
        JOIN record_no_patient_map rpm
          ON rpm.record_no = tpr.extracted_record_no
        WHERE tpr.extracted_record_no IS NOT NULL
          AND TRIM(tpr.extracted_record_no) <> ''
    """, (now_ts,))
    inserted = cur.rowcount
    conn.commit()

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")
    matched = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'payments_recordno'
    """)
    union_patients = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
    """)
    union_coverage = round((union_patients * 100.0 / total_patients), 2) if total_patients else 0.0

    print(f"payments recordno inserted : {inserted:,}")
    print(f"payments matched patients  : {matched:,}")
    print(f"union patients            : {union_patients:,}")
    print(f"union coverage            : {union_coverage:.2f}%")

    conn.close()

if __name__ == "__main__":
    main()
