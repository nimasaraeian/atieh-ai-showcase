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

    print("\n=== Recovery v2 / Phase 02B - Patients Direct ===\n")

    cur.execute("""
        DELETE FROM patient_identity_evidence_v2
        WHERE source = 'patients_direct'
    """)

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
        SELECT
            p.id,
            pc.primary_mobile,
            pc.landline,
            'patients_direct',
            'direct_phone',
            CASE
                WHEN pc.primary_mobile IS NOT NULL AND TRIM(pc.primary_mobile) <> '' THEN 0.95
                ELSE 0.75
            END,
            1,
            ?
        FROM patients p
        JOIN phone_candidates pc
          ON pc.source_table = 'patients'
         AND pc.source_row_id = p.id
        WHERE (pc.primary_mobile IS NOT NULL AND TRIM(pc.primary_mobile) <> '')
           OR (pc.landline IS NOT NULL AND TRIM(pc.landline) <> '')
    """, (datetime.now().isoformat(timespec="seconds"),))

    conn.commit()

    total_patients = scalar(cur, "SELECT COUNT(*) FROM patients")
    matched = scalar(cur, """
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
        WHERE source = 'patients_direct'
    """)
    coverage = round((matched * 100.0 / total_patients), 2) if total_patients else 0.0

    print(f"matched patients : {matched:,}")
    print(f"coverage         : {coverage:.2f}%")

    conn.close()

if __name__ == "__main__":
    main()
