# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db")

def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else 0

def main():
    print(f"DB_PATH = {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Recovery v2 / Phase 04B - Appointment Phone Plus Name ===\n")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source = 'appointment_bridge_combined'
    """)
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
            pl.patient_id,
            aph.appointment_phone_norm,
            NULL,
            'appointment_bridge_combined',
            'phone_plus_name',
            0.97,
            1,
            ?
        FROM appointment_phone_helper aph
        JOIN appointment_recordno_bridge arb
          ON arb.id = aph.arb_id
        JOIN patient_lookup_norm pl
          ON pl.patient_name_norm = arb.patient_name_norm
         AND pl.patient_phone_norm = aph.appointment_phone_norm
        WHERE arb.patient_name_norm IS NOT NULL
          AND TRIM(arb.patient_name_norm) <> ''
          AND pl.patient_name_norm IS NOT NULL
          AND TRIM(pl.patient_name_norm) <> ''
          AND aph.appointment_phone_norm IS NOT NULL
          AND TRIM(aph.appointment_phone_norm) <> ''
          AND pl.patient_phone_norm IS NOT NULL
          AND TRIM(pl.patient_phone_norm) <> ''
    """, (now_ts,))
    inserted = cur.rowcount
    conn.commit()

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")
    matched = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'appointment_bridge_combined'
    """)
    union_all = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source IN (
            'patients_direct',
            'payments_repaired',
            'appointment_bridge_repaired',
            'appointment_bridge_combined'
        )
    """)
    coverage_union = round((union_all * 100.0 / total_patients), 2) if total_patients else 0.0

    print(f"inserted rows       : {inserted:,}")
    print(f"matched patients    : {matched:,}")
    print(f"union patients      : {union_all:,}")
    print(f"union coverage      : {coverage_union:.2f}%")

    conn.close()

if __name__ == "__main__":
    main()
