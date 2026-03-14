# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic.db"

PHASE_NAME = "phase_03_record_bridge"

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else 0

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Recovery v2 / Phase 03 - Appointment Record Bridge ===\n")

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source = 'appointment_record_bridge'
    """)

    cur.execute("""
        DELETE FROM recovery_run_metrics_v2
        WHERE phase_name = ?
    """, (PHASE_NAME,))

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
            prm.patient_id,
            arb.phone_norm AS candidate_mobile,
            NULL AS candidate_landline,
            'appointment_record_bridge' AS source,
            'record_no_bridge' AS evidence_type,
            0.85 AS confidence,
            1 AS match_rank,
            ? AS created_at
        FROM appointment_recordno_bridge arb
        JOIN patient_recordno_map prm
          ON arb.record_no = prm.record_no
        WHERE arb.record_no IS NOT NULL
          AND TRIM(arb.record_no) <> ''
          AND prm.record_no IS NOT NULL
          AND TRIM(prm.record_no) <> ''
          AND arb.phone_norm IS NOT NULL
          AND TRIM(arb.phone_norm) <> ''
    """, (now_ts,))

    inserted_rows = cur.rowcount
    conn.commit()

    matched_patients = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'appointment_record_bridge'
    """)

    coverage = round((matched_patients * 100.0 / total_patients), 2) if total_patients else 0.0

    cur.execute("""
        INSERT INTO recovery_run_metrics_v2
        (phase_name, total_patients, recovered_count, coverage_percent, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (PHASE_NAME, total_patients, matched_patients, coverage, datetime.now().isoformat(timespec="seconds")))

    conn.commit()
    conn.close()

    print(f"inserted rows      : {inserted_rows:,}")
    print(f"matched patients   : {matched_patients:,}")
    print(f"coverage           : {coverage:.2f}%")
    print("\nPhase 03 completed.\n")

if __name__ == "__main__":
    main()
