#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3: Map appointment_recordno_bridge to patients table.
Produces patient_recordno_map (resolved) and patient_recordno_map_review (unresolved/ambiguous).
Matching: A) name+phone exact, B) name+year evidence, C) name unique only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DB_PATH = REPO / "atieh_clinic.db"


def _norm_name(s: str | None) -> str:
    if s is None or (isinstance(s, float) and str(s) == "nan"):
        return ""
    t = str(s).strip().replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return " ".join(t.split())


def _norm_phone(s: str | None) -> str | None:
    if s is None or (isinstance(s, float) and str(s) == "nan"):
        return None
    digits = "".join(c for c in str(s) if c.isdigit())
    if not digits:
        return None
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    if len(digits) > 11:
        digits = digits[-11:]
    if len(digits) < 10:
        return None
    return digits


def ensure_schema(conn):
    mig = REPO / "app" / "db" / "migrations" / "014_patient_recordno_map.sql"
    if mig.exists():
        with open(mig, encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    import sqlite3

    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    cur = conn.cursor()

    # Check bridge exists and has data
    try:
        bridge_count = cur.execute("SELECT COUNT(*) FROM appointment_recordno_bridge").fetchone()[0]
    except sqlite3.OperationalError:
        print("Run build_appointment_recordno_bridge.py first.")
        conn.close()
        return 1
    if bridge_count == 0:
        print("appointment_recordno_bridge is empty. Run build_appointment_recordno_bridge.py first.")
        conn.close()
        return 1

    # One row per record_no with representative name/phone and evidence count
    cur.execute("""
        SELECT record_no,
               MAX(patient_name_norm) AS patient_name_norm,
               MAX(phone_norm) AS phone_norm,
               MAX(appointment_year) AS appointment_year,
               COUNT(*) AS evidence_count
        FROM appointment_recordno_bridge
        WHERE record_no IS NOT NULL AND TRIM(record_no) <> ''
        GROUP BY record_no
    """)
    bridge_rows = cur.fetchall()

    # Patients: id, name_norm, phone_norm, first_visit_year
    patients = cur.execute("SELECT id, name, phone, first_visit_date FROM patients").fetchall()
    patient_list = []
    for pid, name, phone, fv in patients:
        name_n = _norm_name(name)
        phone_n = _norm_phone(phone)
        year = None
        if fv:
            try:
                year = int(str(fv)[:4])
            except Exception:
                pass
        patient_list.append((pid, name_n, phone_n, year))

    # Index by (name_norm, phone_norm) -> list of (patient_id, first_visit_year)
    by_name_phone: dict[tuple[str, str | None], list[tuple[int, int | None]]] = defaultdict(list)
    for pid, name_n, phone_n, year in patient_list:
        key = (name_n, phone_n)
        by_name_phone[key].append((pid, year))

    # Index by name_norm only -> list of patient_id
    by_name_only: dict[str, list[int]] = defaultdict(list)
    for pid, name_n, _pn, _y in patient_list:
        if name_n:
            by_name_only[name_n].append(pid)

    cur.execute("DELETE FROM patient_recordno_map")
    cur.execute("DELETE FROM patient_recordno_map_review")
    conn.commit()

    mapped = 0
    ambiguous = 0
    unresolved = 0

    for (record_no, name_norm, phone_norm, appt_year, evidence_count) in bridge_rows:
        name_norm = (name_norm or "").strip() or ""
        phone_norm = _norm_phone(phone_norm) if phone_norm else None

        # Priority A: exact name + exact phone
        key = (name_norm, phone_norm)
        candidates = by_name_phone.get(key, [])
        if len(candidates) == 1:
            pid = candidates[0][0]
            cur.execute("""
                INSERT INTO patient_recordno_map
                (patient_id, record_no, patient_name_norm, phone_norm, match_method, confidence, evidence_count)
                VALUES (?, ?, ?, ?, 'name_phone', 1.0, ?)
            """, (pid, record_no, name_norm, phone_norm, evidence_count))
            mapped += 1
            continue
        if len(candidates) > 1:
            cur.execute("""
                INSERT INTO patient_recordno_map_review (record_no, patient_name_norm, phone_norm, candidate_patient_ids, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (record_no, name_norm, phone_norm, ",".join(str(c[0]) for c in candidates), "multiple patients same name+phone"))
            ambiguous += 1
            continue

        # Priority B: name + phone match with phone None in bridge (try name + year)
        if not phone_norm and name_norm:
            name_cands = by_name_only.get(name_norm, [])
            if len(name_cands) == 1:
                pid = name_cands[0]
                cur.execute("""
                    INSERT INTO patient_recordno_map
                    (patient_id, record_no, patient_name_norm, phone_norm, match_method, confidence, evidence_count)
                    VALUES (?, ?, ?, ?, 'name_only_unique', 0.85, ?)
                """, (pid, record_no, name_norm, phone_norm, evidence_count))
                mapped += 1
                continue
            if len(name_cands) > 1:
                cur.execute("""
                    INSERT INTO patient_recordno_map_review (record_no, patient_name_norm, phone_norm, candidate_patient_ids, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (record_no, name_norm, phone_norm, ",".join(map(str, name_cands)), "name_unique_ambiguous"))
                ambiguous += 1
                continue

        # Try name only (phone in bridge but no match)
        if name_norm:
            name_cands = by_name_only.get(name_norm, [])
            if len(name_cands) == 1:
                pid = name_cands[0]
                cur.execute("""
                    INSERT INTO patient_recordno_map
                    (patient_id, record_no, patient_name_norm, phone_norm, match_method, confidence, evidence_count)
                    VALUES (?, ?, ?, ?, 'name_only_unique', 0.80, ?)
                """, (pid, record_no, name_norm, phone_norm, evidence_count))
                mapped += 1
                continue
            if len(name_cands) > 1:
                cur.execute("""
                    INSERT INTO patient_recordno_map_review (record_no, patient_name_norm, phone_norm, candidate_patient_ids, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (record_no, name_norm, phone_norm, ",".join(map(str, name_cands)), "name_ambiguous"))
                ambiguous += 1
                continue

        cur.execute("""
            INSERT INTO patient_recordno_map_review (record_no, patient_name_norm, phone_norm, reason)
            VALUES (?, ?, ?, ?)
        """, (record_no, name_norm, phone_norm, "no_match"))
        unresolved += 1

    conn.commit()

    total_bridge = len(bridge_rows)
    review_count = cur.execute("SELECT COUNT(*) FROM patient_recordno_map_review").fetchone()[0]
    map_count = cur.execute("SELECT COUNT(*) FROM patient_recordno_map").fetchone()[0]

    print("\n--- patient_recordno_map ---")
    print(f"Distinct record_no in bridge: {total_bridge}")
    print(f"Mapped to patient_id: {map_count}")
    print(f"Unresolved/ambiguous in review: {review_count}")
    print(f"(mapped + review = {map_count + review_count})")

    top20 = cur.execute("""
        SELECT patient_id, record_no, patient_name_norm, match_method, confidence, evidence_count
        FROM patient_recordno_map
        ORDER BY evidence_count DESC, confidence DESC
        LIMIT 20
    """).fetchall()
    print("\nTop 20 sample mappings:")
    for r in top20:
        print(f"  {r}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
