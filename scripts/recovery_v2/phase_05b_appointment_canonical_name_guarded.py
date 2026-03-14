# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db")

GENERIC_NAMES = {"دندانپزشکی", "nan", ""}

def canonical_name(name: str):
    if not name:
        return None
    parts = [p.strip() for p in name.split() if p.strip()]
    parts = sorted(parts)
    return " ".join(parts)

def main():
    print(f"DB_PATH = {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Phase 05B – Appointment Canonical Name Guarded ===\n")

    cur.execute("DROP TABLE IF EXISTS tmp_patient_canon")
    cur.execute("DROP TABLE IF EXISTS tmp_appt_canon")

    cur.execute("""
        CREATE TABLE tmp_patient_canon (
            patient_id INTEGER,
            canon_name TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE tmp_appt_canon (
            canon_name TEXT,
            phone_norm TEXT
        )
    """)

    # --- load patients ---
    rows = cur.execute("""
        SELECT patient_id, patient_name_norm
        FROM patient_lookup_norm
        WHERE patient_phone_norm IS NULL
          AND TRIM(patient_name_norm) <> ''
    """).fetchall()

    patient_map = {}
    for pid, name in rows:
        if name in GENERIC_NAMES:
            continue
        c = canonical_name(name)
        if not c:
            continue
        patient_map.setdefault(c, []).append(pid)

    # keep only low frequency
    data = []
    for cname, ids in patient_map.items():
        if len(ids) <= 2:
            for pid in ids:
                data.append((pid, cname))

    cur.executemany(
        "INSERT INTO tmp_patient_canon (patient_id, canon_name) VALUES (?,?)",
        data
    )

    # --- load appointments ---
    rows = cur.execute("""
        SELECT patient_name_norm, phone_norm
        FROM appointment_recordno_bridge
        WHERE patient_name_norm IS NOT NULL
          AND TRIM(patient_name_norm) <> ''
          AND phone_norm IS NOT NULL
    """).fetchall()

    appt_data = []
    for name, phone in rows:
        if name in GENERIC_NAMES:
            continue
        c = canonical_name(name)
        if not c:
            continue
        appt_data.append((c, phone))

    cur.executemany(
        "INSERT INTO tmp_appt_canon (canon_name, phone_norm) VALUES (?,?)",
        appt_data
    )

    conn.commit()

    cur.execute("""
        INSERT INTO patient_identity_evidence_v2
        (
            patient_id,
            candidate_mobile,
            source,
            evidence_type,
            confidence,
            match_rank,
            created_at
        )
        SELECT DISTINCT
            p.patient_id,
            a.phone_norm,
            'appointment_canonical',
            'canonical_name_match',
            0.91,
            1,
            ?
        FROM tmp_patient_canon p
        JOIN tmp_appt_canon a
          ON p.canon_name = a.canon_name
    """, (datetime.now().isoformat(timespec="seconds"),))

    inserted = cur.rowcount
    conn.commit()

    total_patients = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]

    union_patients = cur.execute("""
        SELECT COUNT(DISTINCT patient_id)
        FROM patient_identity_evidence_v2
    """).fetchone()[0]

    coverage = round((union_patients * 100.0 / total_patients), 2)

    print(f"inserted rows : {inserted}")
    print(f"union patients: {union_patients}")
    print(f"coverage      : {coverage}%")

    conn.close()

if __name__ == "__main__":
    main()
