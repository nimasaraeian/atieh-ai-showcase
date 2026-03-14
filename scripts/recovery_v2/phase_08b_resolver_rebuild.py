# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db")

SOURCE_PRIORITY = {
    "appointment_bridge_combined": 100,
    "payments_recordno": 95,
    "appointment_canonical": 90,
    "patients_direct": 85,
    "appointment_bridge_repaired": 80,
    "payments_repaired": 75,
    "payments_canonical": 70,
}

def main():
    print(f"DB_PATH = {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Phase 08B - Resolver / Rebuild V2 ===\n")

    cur.execute("DELETE FROM patient_phone_resolved_v2")
    cur.execute("DELETE FROM patient_phone_recovered_v2")
    conn.commit()

    rows = cur.execute("""
        SELECT
            patient_id,
            candidate_mobile,
            candidate_landline,
            source,
            evidence_type,
            confidence,
            created_at
        FROM patient_identity_evidence_v2
        ORDER BY patient_id
    """).fetchall()

    grouped = {}
    for row in rows:
        patient_id = row[0]
        grouped.setdefault(patient_id, []).append(row)

    resolved = []

    for patient_id, evidences in grouped.items():
        def score(ev):
            source = ev[3]
            confidence = ev[5] or 0
            return (confidence, SOURCE_PRIORITY.get(source, 0))

        best = sorted(evidences, key=score, reverse=True)[0]

        best_mobile = None
        best_landline = None

        mobile_candidates = [e for e in evidences if e[1] and str(e[1]).strip()]
        landline_candidates = [e for e in evidences if e[2] and str(e[2]).strip()]

        if mobile_candidates:
            best_mobile = sorted(mobile_candidates, key=score, reverse=True)[0][1]

        if landline_candidates:
            best_landline = sorted(landline_candidates, key=score, reverse=True)[0][2]

        resolved.append((
            patient_id,
            best_mobile,
            best_landline,
            best[3],
            best[4],
            best[5],
            datetime.now().isoformat(timespec="seconds"),
        ))

    cur.executemany("""
        INSERT INTO patient_phone_resolved_v2
        (patient_id, mobile, landline, best_source, best_evidence_type, confidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, resolved)

    cur.executemany("""
        INSERT INTO patient_phone_recovered_v2
        (patient_id, mobile, landline, best_source, confidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (r[0], r[1], r[2], r[3], r[5], r[6]) for r in resolved
    ])

    conn.commit()

    total_patients = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    recovered = cur.execute("SELECT COUNT(*) FROM patient_phone_recovered_v2").fetchone()[0]
    coverage = round((recovered * 100.0 / total_patients), 2) if total_patients else 0.0

    print(f"recovered patients : {recovered:,}")
    print(f"coverage           : {coverage:.2f}%")

    conn.close()

if __name__ == "__main__":
    main()
