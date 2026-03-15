# -*- coding: utf-8 -*-
"""
Build identity candidate matches: payment↔patient, appointment↔patient, payment↔appointment.
Phase 1A: high-confidence rules (A1–A5). Phase 1B: composite rules (B1–B7).
Stores candidates only; scoring/tier in build_identity_match_scores.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"
sys.path.insert(0, str(REPO))

from scripts.helpers.name_cleanup import name_exact_key_match, name_similarity_score

# High-confidence rules (Phase 1A)
# A1: national_id exact
# A2: phone exact + name exact
# A3: phone exact + very high name similarity
# A4: record_no exact + name support
# A5: exact name + same year + supporting phone presence

# Composite rules (Phase 1B)
# B1: phone exact only
# B2: name exact only
# B3: name similarity high only
# B4: phone exact + close date
# B5: name exact + same year
# B6: record_no exact only
# B7: payment↔appointment via phone; then appointment↔patient via phone/name

NAME_SIMILARITY_STRICT = 90.0  # for A3
NAME_SIMILARITY_HIGH = 75.0    # for B3


def run_schema(conn) -> None:
    for name in ("001_identity_resolution_schema.sql", "002_identity_resolution_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _insert_candidate(conn, left_type, left_id, right_type, right_id, rule,
                      name_exact, name_sim, phone_exact, nid_exact, record_exact, same_year, date_prox):
    conn.execute("""
        INSERT INTO identity_candidate_matches (
            left_source_type, left_row_id, right_source_type, right_row_id, candidate_rule,
            name_exact_flag, name_similarity_score, phone_exact_flag, national_id_exact_flag,
            record_no_exact_flag, same_year_flag, date_proximity_flag, match_status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'proposed')
    """, (left_type, left_id, right_type, right_id, rule,
          int(name_exact), name_sim, int(phone_exact), int(nid_exact), int(record_exact), int(same_year), int(date_prox)))


def build_payment_patient(conn) -> int:
    """Payment ↔ Patient: A1, A2, A3, A4, B1, B2, B3, B5, B6."""
    conn.execute("DELETE FROM identity_candidate_matches WHERE left_source_type = 'payment' AND right_source_type = 'patient'")
    conn.execute("DELETE FROM identity_candidate_matches WHERE left_source_type = 'patient' AND right_source_type = 'payment'")
    conn.commit()

    pay = conn.execute("""
        SELECT id, payments_staging_id, patient_name_norm, patient_name_key, mobile_primary_norm,
               national_id_norm, record_no_norm, shamsi_year
        FROM identity_normalized_payments
    """).fetchall()
    pt = conn.execute("""
        SELECT id, patient_id, patient_name_norm, patient_name_key, phone_primary_norm,
               national_id_norm, record_no_norm
        FROM patients_identity_normalized
    """).fetchall()

    by_phone_pt = {}
    by_nid_pt = {}
    by_key_pt = {}
    by_rec_pt = {}
    for r in pt:
        pid, patient_id, name_n, name_k, ph, nid, rec = r
        if ph:
            by_phone_pt.setdefault(ph, []).append(r)
        if nid:
            by_nid_pt.setdefault(nid, []).append(r)
        if name_k:
            by_key_pt.setdefault(name_k, []).append(r)
        if rec:
            by_rec_pt.setdefault(rec, []).append(r)

    count = 0
    for p in pay:
        (inp_id, staging_id, pname_n, pname_k, pphone, pnid, prec, pyear) = p
        left_id = staging_id  # we store payments_staging_id as left_row_id for payment
        left_type, right_type = "payment", "patient"

        # A1: national_id exact
        if pnid and pnid in by_nid_pt:
            for r in by_nid_pt[pnid]:
                name_exact = (pname_k == r[3]) if (pname_k and r[3]) else False
                name_sim = 100.0 if name_exact else name_similarity_score(pname_n, r[2])
                _insert_candidate(conn, left_type, left_id, right_type, r[1], "A1_national_id_exact",
                                  int(name_exact), name_sim, 0, 1, 0, 0, 0)
                count += 1

        # By phone
        if pphone and pphone in by_phone_pt:
            for r in by_phone_pt[pphone]:
                pid, patient_id, rname_n, rname_k, rph, rnid, rrec = r
                name_exact = name_exact_key_match(pname_k, rname_k)
                name_sim = name_similarity_score(pname_n, rname_n)
                # A2: phone exact + name exact
                if name_exact:
                    _insert_candidate(conn, left_type, left_id, right_type, patient_id, "A2_phone_exact_name_exact", 1, 100.0, 1, 0, 0, 0, 0)
                    count += 1
                # A3: phone exact + very high name similarity
                elif name_sim >= NAME_SIMILARITY_STRICT:
                    _insert_candidate(conn, left_type, left_id, right_type, patient_id, "A3_phone_exact_name_high_sim", 0, name_sim, 1, 0, 0, 0, 0)
                    count += 1
                # B1: phone exact only
                else:
                    _insert_candidate(conn, left_type, left_id, right_type, patient_id, "B1_phone_exact_only", 0, name_sim, 1, 0, 0, 0, 0)
                    count += 1

        # A4: record_no exact + name support
        if prec and prec in by_rec_pt:
            for r in by_rec_pt[prec]:
                pid, patient_id, rname_n, rname_k, rph, rnid, rrec = r
                if name_exact_key_match(pname_k, rname_k) or name_similarity_score(pname_n, rname_n) >= NAME_SIMILARITY_HIGH:
                    _insert_candidate(conn, left_type, left_id, right_type, patient_id, "A4_record_no_exact_name_support", int(name_exact_key_match(pname_k, rname_k)), name_similarity_score(pname_n, rname_n), int(pphone == rph), 0, 1, 0, 0)
                    count += 1

        # B2/B5: name exact (with or without same year) – only if no stronger match already
        if pname_k and pname_k in by_key_pt:
            for r in by_key_pt[pname_k]:
                patient_id, rname_n, rname_k = r[1], r[2], r[3]
                _insert_candidate(conn, left_type, left_id, right_type, patient_id, "B2_name_exact_only", 1, 100.0, 0, 0, 0, 0, 0)
                count += 1

        # B6: record_no exact only
        if prec and prec in by_rec_pt:
            for r in by_rec_pt[prec]:
                if r[1] not in [x[1] for x in by_phone_pt.get(pphone or "", [])]:
                    _insert_candidate(conn, left_type, left_id, right_type, r[1], "B6_record_no_exact_only", 0, name_similarity_score(pname_n, r[2]), 0, 0, 1, 0, 0)
                    count += 1
    conn.commit()
    return count


def build_appointment_patient(conn) -> int:
    """Appointment ↔ Patient: A2, A3, A4, B1, B2, B3, B5, B6."""
    conn.execute("DELETE FROM identity_candidate_matches WHERE left_source_type = 'appointment' AND right_source_type = 'patient'")
    conn.execute("DELETE FROM identity_candidate_matches WHERE left_source_type = 'patient' AND right_source_type = 'appointment'")
    conn.commit()

    app = conn.execute("""
        SELECT id, appointment_staging_id, patient_name_norm, patient_name_key, phone_primary_norm,
               national_id_norm, record_no_norm, shamsi_year
        FROM identity_normalized_appointments
    """).fetchall()
    pt = conn.execute("""
        SELECT id, patient_id, patient_name_norm, patient_name_key, phone_primary_norm,
               national_id_norm, record_no_norm
        FROM patients_identity_normalized
    """).fetchall()

    by_phone_pt = {r[4]: r for r in pt if r[4]}
    by_key_pt = {}
    for r in pt:
        if r[3]:
            by_key_pt.setdefault(r[3], []).append(r)
    by_rec_pt = {}
    for r in pt:
        if r[6]:
            by_rec_pt.setdefault(r[6], []).append(r)

    count = 0
    for a in app:
        (ina_id, staging_id, aname_n, aname_k, aphone, anid, arec, ayear) = a
        left_id = staging_id
        left_type, right_type = "appointment", "patient"

        if aphone and aphone in by_phone_pt:
            r = by_phone_pt[aphone]
            patient_id, rname_n, rname_k = r[1], r[2], r[3]
            name_exact = name_exact_key_match(aname_k, rname_k)
            name_sim = name_similarity_score(aname_n, rname_n)
            if name_exact:
                _insert_candidate(conn, left_type, left_id, right_type, patient_id, "A2_phone_exact_name_exact", 1, 100.0, 1, 0, 0, 0, 0)
                count += 1
            elif name_sim >= NAME_SIMILARITY_STRICT:
                _insert_candidate(conn, left_type, left_id, right_type, patient_id, "A3_phone_exact_name_high_sim", 0, name_sim, 1, 0, 0, 0, 0)
                count += 1
            else:
                _insert_candidate(conn, left_type, left_id, right_type, patient_id, "B1_phone_exact_only", 0, name_sim, 1, 0, 0, 0, 0)
                count += 1

        if aname_k and aname_k in by_key_pt:
            for r in by_key_pt[aname_k]:
                _insert_candidate(conn, left_type, left_id, right_type, r[1], "B2_name_exact_only", 1, 100.0, 0, 0, 0, 0, 0)
                count += 1

        if arec and arec in by_rec_pt:
            for r in by_rec_pt[arec]:
                name_sim = name_similarity_score(aname_n, r[2])
                if name_sim >= NAME_SIMILARITY_HIGH or name_exact_key_match(aname_k, r[3]):
                    _insert_candidate(conn, left_type, left_id, right_type, r[1], "A4_record_no_exact_name_support", int(name_exact_key_match(aname_k, r[3])), name_sim, 0, 0, 1, 0, 0)
                    count += 1
                else:
                    _insert_candidate(conn, left_type, left_id, right_type, r[1], "B6_record_no_exact_only", 0, name_sim, 0, 0, 1, 0, 0)
                    count += 1
    conn.commit()
    return count


def build_payment_appointment(conn) -> int:
    """Payment ↔ Appointment: phone exact (B7 style); then we can link appointment→patient elsewhere."""
    conn.execute("DELETE FROM identity_candidate_matches WHERE left_source_type = 'payment' AND right_source_type = 'appointment'")
    conn.execute("DELETE FROM identity_candidate_matches WHERE left_source_type = 'appointment' AND right_source_type = 'payment'")
    conn.commit()

    pay = conn.execute("""
        SELECT id, payments_staging_id, patient_name_norm, patient_name_key, mobile_primary_norm, shamsi_year
        FROM identity_normalized_payments
    """).fetchall()
    app = conn.execute("""
        SELECT id, appointment_staging_id, patient_name_norm, patient_name_key, phone_primary_norm, shamsi_year
        FROM identity_normalized_appointments
    """).fetchall()

    by_phone_app = {}
    for r in app:
        if r[4]:
            by_phone_app.setdefault(r[4], []).append(r)

    count = 0
    for p in pay:
        (inp_id, staging_id, pname_n, pname_k, pphone, pyear) = p
        if not pphone or pphone not in by_phone_app:
            continue
        for r in by_phone_app[pphone]:
            astaging_id, aname_n, aname_k, aphone, ayear = r[1], r[2], r[3], r[4], r[5]
            name_exact = name_exact_key_match(pname_k, aname_k)
            name_sim = name_similarity_score(pname_n, aname_n)
            same_year = 1 if pyear == ayear else 0
            _insert_candidate(conn, "payment", staging_id, "appointment", astaging_id, "B7_payment_appointment_phone_exact",
                              int(name_exact), name_sim, 1, 0, 0, same_year, 0)
            count += 1
    conn.commit()
    return count


def main():
    import sqlite3

    db_path = os.environ.get("ATIEH_DB_PATH") or os.environ.get("DB_PATH") or str(REPO / "atieh_clinic_recovery81_test.db")
    db_path = Path(db_path)
    if not db_path.is_absolute():
        db_path = REPO / db_path
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA busy_timeout = 30000")
    run_schema(conn)

    print("Building identity candidate matches...")
    n1 = build_payment_patient(conn)
    print(f"  payment↔patient: {n1} candidates")
    n2 = build_appointment_patient(conn)
    print(f"  appointment↔patient: {n2} candidates")
    n3 = build_payment_appointment(conn)
    print(f"  payment↔appointment: {n3} candidates")
    total = conn.execute("SELECT COUNT(*) FROM identity_candidate_matches").fetchone()[0]
    print(f"  Total candidates: {total}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
