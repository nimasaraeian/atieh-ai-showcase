# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic.db"

PHASE_PAYMENTS = "phase_02_exact_phone::payments"
PHASE_APPOINTMENTS = "phase_02_exact_phone::appointments"
PHASE_TOTAL = "phase_02_exact_phone::total"

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else 0

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Recovery v2 / Phase 02 - Exact Phone Matches ===\n")

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source IN ('payments_exact_phone', 'appointments_exact_phone')
    """)

    cur.execute("""
        DELETE FROM recovery_run_metrics_v2
        WHERE phase_name IN (?, ?, ?)
    """, (PHASE_PAYMENTS, PHASE_APPOINTMENTS, PHASE_TOTAL))

    conn.commit()

    now_1 = datetime.now().isoformat(timespec="seconds")

    print("[1/2] inserting payments exact-phone evidence ...")
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
            pl.patient_id AS patient_id,
            CASE
                WHEN p.phone_type = 'mobile' THEN p.payment_phone_norm
                ELSE NULL
            END AS candidate_mobile,
            CASE
                WHEN p.phone_type = 'landline' THEN p.payment_phone_norm
                ELSE NULL
            END AS candidate_landline,
            'payments_exact_phone' AS source,
            'exact_phone' AS evidence_type,
            1.00 AS confidence,
            1 AS match_rank,
            ? AS created_at
        FROM patient_lookup_norm pl
        JOIN payments_lookup_norm p
          ON pl.patient_phone_norm = p.payment_phone_norm
        WHERE pl.patient_phone_norm IS NOT NULL
          AND TRIM(pl.patient_phone_norm) <> ''
          AND p.payment_phone_norm IS NOT NULL
          AND TRIM(p.payment_phone_norm) <> ''
    """, (now_1,))
    payments_inserted = cur.rowcount
    conn.commit()
    print(f"    inserted: {payments_inserted:,}")

    now_2 = datetime.now().isoformat(timespec="seconds")

    print("[2/2] inserting appointments exact-phone evidence ...")
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
            pl.patient_id AS patient_id,
            aph.appointment_phone_norm AS candidate_mobile,
            NULL AS candidate_landline,
            'appointments_exact_phone' AS source,
            'exact_phone' AS evidence_type,
            0.95 AS confidence,
            1 AS match_rank,
            ? AS created_at
        FROM patient_lookup_norm pl
        JOIN appointment_phone_helper aph
          ON pl.patient_phone_norm = aph.appointment_phone_norm
        WHERE pl.patient_phone_norm IS NOT NULL
          AND TRIM(pl.patient_phone_norm) <> ''
          AND aph.appointment_phone_norm IS NOT NULL
          AND TRIM(aph.appointment_phone_norm) <> ''
    """, (now_2,))
    appointments_inserted = cur.rowcount
    conn.commit()
    print(f"    inserted: {appointments_inserted:,}")

    payments_patients = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'payments_exact_phone'
    """)

    appointments_patients = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'appointments_exact_phone'
    """)

    total_patients_matched = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source IN ('payments_exact_phone', 'appointments_exact_phone')
    """)

    payments_coverage = round((payments_patients * 100.0 / total_patients), 2) if total_patients else 0.0
    appointments_coverage = round((appointments_patients * 100.0 / total_patients), 2) if total_patients else 0.0
    total_coverage = round((total_patients_matched * 100.0 / total_patients), 2) if total_patients else 0.0

    now_ts = datetime.now().isoformat(timespec="seconds")

    cur.executemany("""
        INSERT INTO recovery_run_metrics_v2
        (phase_name, total_patients, recovered_count, coverage_percent, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (PHASE_PAYMENTS, total_patients, payments_patients, payments_coverage, now_ts),
        (PHASE_APPOINTMENTS, total_patients, appointments_patients, appointments_coverage, now_ts),
        (PHASE_TOTAL, total_patients, total_patients_matched, total_coverage, now_ts),
    ])

    conn.commit()
    conn.close()

    print("\n=== Phase 02 completed ===")
    print(f"payments distinct patients     : {payments_patients:,}")
    print(f"appointments distinct patients : {appointments_patients:,}")
    print(f"total distinct patients        : {total_patients_matched:,}")
    print(f"total coverage                 : {total_coverage:.2f}%\n")

if __name__ == "__main__":
    main()
