# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic.db"

PHASE_NAME = "phase_04_last8_safe"

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else 0

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Recovery v2 / Phase 04 - Last8 Safe Matching ===\n")

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source = 'last8_safe'
    """)

    cur.execute("""
        DELETE FROM recovery_run_metrics_v2
        WHERE phase_name = ?
    """, (PHASE_NAME,))

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
        WITH unique_payment_last8 AS (
            SELECT
                payment_phone_last8,
                MIN(payment_phone_norm) AS payment_phone_norm
            FROM payments_lookup_norm
            WHERE payment_phone_last8 IS NOT NULL
              AND TRIM(payment_phone_last8) <> ''
              AND payment_phone_norm IS NOT NULL
              AND TRIM(payment_phone_norm) <> ''
            GROUP BY payment_phone_last8
            HAVING COUNT(DISTINCT payment_phone_norm) = 1
        )
        SELECT DISTINCT
            pl.patient_id,
            upl.payment_phone_norm AS candidate_mobile,
            NULL AS candidate_landline,
            'last8_safe' AS source,
            'last8_unique_payment' AS evidence_type,
            0.65 AS confidence,
            1 AS match_rank,
            ? AS created_at
        FROM patient_lookup_norm pl
        JOIN unique_payment_last8 upl
          ON pl.patient_phone_last8 = upl.payment_phone_last8
        WHERE pl.patient_phone_last8 IS NOT NULL
          AND TRIM(pl.patient_phone_last8) <> ''
          AND upl.payment_phone_norm IS NOT NULL
          AND TRIM(upl.payment_phone_norm) <> ''
          AND (pl.patient_phone_norm IS NULL OR TRIM(pl.patient_phone_norm) = '' OR pl.patient_phone_norm <> upl.payment_phone_norm)
    """, (now_1,))
    inserted_from_payments = cur.rowcount
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
        WITH unique_appointment_last8 AS (
            SELECT
                appointment_phone_last8,
                MIN(appointment_phone_norm) AS appointment_phone_norm
            FROM appointment_phone_helper
            WHERE appointment_phone_last8 IS NOT NULL
              AND TRIM(appointment_phone_last8) <> ''
              AND appointment_phone_norm IS NOT NULL
              AND TRIM(appointment_phone_norm) <> ''
            GROUP BY appointment_phone_last8
            HAVING COUNT(DISTINCT appointment_phone_norm) = 1
        )
        SELECT DISTINCT
            pl.patient_id,
            ual.appointment_phone_norm AS candidate_mobile,
            NULL AS candidate_landline,
            'last8_safe' AS source,
            'last8_unique_appointment' AS evidence_type,
            0.65 AS confidence,
            1 AS match_rank,
            ? AS created_at
        FROM patient_lookup_norm pl
        JOIN unique_appointment_last8 ual
          ON pl.patient_phone_last8 = ual.appointment_phone_last8
        WHERE pl.patient_phone_last8 IS NOT NULL
          AND TRIM(pl.patient_phone_last8) <> ''
          AND ual.appointment_phone_norm IS NOT NULL
          AND TRIM(ual.appointment_phone_norm) <> ''
          AND (pl.patient_phone_norm IS NULL OR TRIM(pl.patient_phone_norm) = '' OR pl.patient_phone_norm <> ual.appointment_phone_norm)
    """, (now_2,))
    inserted_from_appointments = cur.rowcount
    conn.commit()

    matched_patients = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'last8_safe'
    """)

    coverage = round((matched_patients * 100.0 / total_patients), 2) if total_patients else 0.0

    cur.execute("""
        INSERT INTO recovery_run_metrics_v2
        (phase_name, total_patients, recovered_count, coverage_percent, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (PHASE_NAME, total_patients, matched_patients, coverage, datetime.now().isoformat(timespec="seconds")))

    conn.commit()
    conn.close()

    print(f"inserted from payments      : {inserted_from_payments:,}")
    print(f"inserted from appointments  : {inserted_from_appointments:,}")
    print(f"matched patients           : {matched_patients:,}")
    print(f"coverage                   : {coverage:.2f}%")
    print("\nPhase 04 completed.\n")

if __name__ == "__main__":
    main()
