# -*- coding: utf-8 -*-
"""
Phase 3: Build anchor patient list and anchor evidence tables from safe_identity_matches_phase2.
Populates: identity_anchor_patients_phase3, identity_anchor_profile_phase3,
identity_anchor_phone_phase3, identity_anchor_recordno_phase3, identity_anchor_name_phase3.
Does NOT update patients or payments.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"


def run_schema(conn) -> None:
    for name in ("004_phase3_graph_expansion_schema.sql", "005_phase3_graph_expansion_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _collect_phones(s: str | None) -> list[str]:
    if not s:
        return []
    try:
        out = json.loads(s)
        return [x for x in out if x and isinstance(x, str)]
    except Exception:
        return []


def build_anchors_and_evidence(conn) -> None:
    # Clear phase3 anchor tables
    for t in (
        "identity_anchor_name_phase3",
        "identity_anchor_recordno_phase3",
        "identity_anchor_phone_phase3",
        "identity_anchor_profile_phase3",
        "identity_anchor_patients_phase3",
    ):
        conn.execute(f"DELETE FROM {t}")
    conn.commit()

    # Safe matches where right = patient
    safe = conn.execute("""
        SELECT left_source_type, left_row_id, right_row_id, promotion_reason
        FROM safe_identity_matches_phase2
        WHERE right_source_type = 'patient'
    """).fetchall()

    # Lookups: left_row_id -> normalized fields
    pay_rows = conn.execute("""
        SELECT payments_staging_id, mobile_primary_norm, mobile_all_norm_json,
               record_no_norm, patient_name_key, patient_name_norm, shamsi_year, admission_date_norm
        FROM identity_normalized_payments
    """).fetchall()
    pay_by_id = {r[0]: r for r in pay_rows}

    app_rows = conn.execute("""
        SELECT appointment_staging_id, phone_primary_norm, phone_all_norm_json,
               record_no_norm, patient_name_key, patient_name_norm, shamsi_year, appointment_date_norm
        FROM identity_normalized_appointments
    """).fetchall()
    app_by_id = {r[0]: r for r in app_rows}

    pt_rows = conn.execute("""
        SELECT patient_id, phone_primary_norm, phone_all_norm_json,
               record_no_norm, patient_name_key, patient_name_norm
        FROM patients_identity_normalized
    """).fetchall()
    pt_by_id = {r[0]: r for r in pt_rows}

    # Per-patient aggregates
    anchor_match_count = defaultdict(int)
    primary_anchor_count = defaultdict(int)
    high_sim_anchor_count = defaultdict(int)
    phone_only_anchor_count = defaultdict(int)
    phones = defaultdict(lambda: defaultdict(lambda: {"obs": 0, "pay": 0, "app": 0, "pt": 0}))
    record_nos = defaultdict(lambda: defaultdict(lambda: {"obs": 0, "pay": 0, "pt": 0}))
    names = defaultdict(lambda: defaultdict(lambda: {"obs": 0, "pay": 0, "app": 0, "pt": 0, "norm": None}))
    years = defaultdict(set)
    dates = []
    linked_payments = defaultdict(set)
    linked_appointments = defaultdict(set)

    for left_type, left_id, patient_id, promotion_reason in safe:
        anchor_match_count[patient_id] += 1
        if promotion_reason == "primary_anchor":
            primary_anchor_count[patient_id] += 1
        elif promotion_reason == "A3_phone_exact_name_high_sim":
            high_sim_anchor_count[patient_id] += 1
        elif promotion_reason == "B1_phone_exact_only":
            phone_only_anchor_count[patient_id] += 1

        if left_type == "payment":
            linked_payments[patient_id].add(left_id)
            row = pay_by_id.get(left_id)
            if row:
                _, mobile_prim, mobile_all, rec_no, name_k, name_n, year, date_norm = row
                for ph in ([mobile_prim] if mobile_prim else []) + _collect_phones(mobile_all):
                    if ph:
                        phones[patient_id][ph]["obs"] += 1
                        phones[patient_id][ph]["pay"] += 1
                if rec_no:
                    record_nos[patient_id][rec_no]["obs"] += 1
                    record_nos[patient_id][rec_no]["pay"] += 1
                if name_k:
                    names[patient_id][name_k]["obs"] += 1
                    names[patient_id][name_k]["pay"] += 1
                    names[patient_id][name_k]["norm"] = name_n
                if year is not None:
                    years[patient_id].add(year)
                if date_norm:
                    dates.append((patient_id, date_norm))

        elif left_type == "appointment":
            linked_appointments[patient_id].add(left_id)
            row = app_by_id.get(left_id)
            if row:
                _, phone_prim, phone_all, rec_no, name_k, name_n, year, date_norm = row
                for ph in ([phone_prim] if phone_prim else []) + _collect_phones(phone_all):
                    if ph:
                        phones[patient_id][ph]["obs"] += 1
                        phones[patient_id][ph]["app"] += 1
                if rec_no:
                    record_nos[patient_id][rec_no]["obs"] += 1
                    record_nos[patient_id][rec_no]["pay"] += 0  # appointments don't have "pay"
                if name_k:
                    names[patient_id][name_k]["obs"] += 1
                    names[patient_id][name_k]["app"] += 1
                    names[patient_id][name_k]["norm"] = name_n
                if year is not None:
                    years[patient_id].add(year)
                if date_norm:
                    dates.append((patient_id, date_norm))

    # Patient-side evidence for each anchor
    for patient_id in set(anchor_match_count):
        row = pt_by_id.get(patient_id)
        if row:
            _, phone_prim, phone_all, rec_no, name_k, name_n = row
            for ph in ([phone_prim] if phone_prim else []) + _collect_phones(phone_all):
                if ph:
                    phones[patient_id][ph]["obs"] += 1
                    phones[patient_id][ph]["pt"] += 1
            if rec_no:
                record_nos[patient_id][rec_no]["obs"] += 1
                record_nos[patient_id][rec_no]["pt"] += 1
            if name_k:
                names[patient_id][name_k]["obs"] += 1
                names[patient_id][name_k]["pt"] += 1
                names[patient_id][name_k]["norm"] = name_n

    # Insert identity_anchor_patients_phase3
    ins_anchor = """
        INSERT INTO identity_anchor_patients_phase3
        (patient_id, anchor_match_count, primary_anchor_count, high_sim_anchor_count, phone_only_anchor_count)
        VALUES (?, ?, ?, ?, ?)
    """
    for patient_id in anchor_match_count:
        conn.execute(ins_anchor, (
            patient_id,
            anchor_match_count[patient_id],
            primary_anchor_count.get(patient_id, 0),
            high_sim_anchor_count.get(patient_id, 0),
            phone_only_anchor_count.get(patient_id, 0),
        ))
    conn.commit()

    # Insert identity_anchor_phone_phase3
    ins_phone = """
        INSERT INTO identity_anchor_phone_phase3
        (patient_id, phone_norm, observation_count, appears_in_payments_count, appears_in_appointments_count, appears_in_patients_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    for patient_id, ph_dict in phones.items():
        for ph, counts in ph_dict.items():
            if not ph:
                continue
            conn.execute(ins_phone, (
                patient_id, ph,
                counts["obs"], counts["pay"], counts["app"], counts["pt"],
            ))
    conn.commit()

    # Insert identity_anchor_recordno_phase3 (appointments don't have record_no in payments sense; we still count observation)
    ins_rec = """
        INSERT INTO identity_anchor_recordno_phase3
        (patient_id, record_no_norm, observation_count, appears_in_payments_count, appears_in_patients_count)
        VALUES (?, ?, ?, ?, ?)
    """
    for patient_id, rec_dict in record_nos.items():
        for rec, counts in rec_dict.items():
            if not rec:
                continue
            conn.execute(ins_rec, (
                patient_id, rec, counts["obs"], counts["pay"], counts["pt"],
            ))
    conn.commit()

    # Insert identity_anchor_name_phase3
    ins_name = """
        INSERT INTO identity_anchor_name_phase3
        (patient_id, patient_name_key, patient_name_norm, observation_count, appears_in_payments_count, appears_in_appointments_count, appears_in_patients_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    for patient_id, name_dict in names.items():
        for name_k, data in name_dict.items():
            if not name_k:
                continue
            conn.execute(ins_name, (
                patient_id, name_k, data["norm"],
                data["obs"], data["pay"], data["app"], data["pt"],
            ))
    conn.commit()

    # Min/max date per patient
    patient_dates = defaultdict(list)
    for pid, d in dates:
        if d:
            patient_dates[pid].append(d)
    min_max = {}
    for pid, dlist in patient_dates.items():
        try:
            min_max[pid] = (min(dlist), max(dlist))
        except Exception:
            min_max[pid] = (None, None)

    # Insert identity_anchor_profile_phase3
    ins_profile = """
        INSERT INTO identity_anchor_profile_phase3
        (patient_id, phones_json, phone_count, names_json, name_count, record_nos_json, record_no_count,
         years_json, year_count, linked_payments_count, linked_appointments_count, linked_safe_matches_count,
         min_date_norm, max_date_norm)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for patient_id in anchor_match_count:
        ph_list = list(phones.get(patient_id, {}).keys())
        name_list = list(names.get(patient_id, {}).keys())
        rec_list = list(record_nos.get(patient_id, {}).keys())
        year_list = sorted(years.get(patient_id, []))
        mn, mx = min_max.get(patient_id, (None, None))
        conn.execute(ins_profile, (
            patient_id,
            json.dumps(ph_list, ensure_ascii=False) if ph_list else None,
            len(ph_list),
            json.dumps(name_list, ensure_ascii=False) if name_list else None,
            len(name_list),
            json.dumps(rec_list, ensure_ascii=False) if rec_list else None,
            len(rec_list),
            json.dumps(year_list, ensure_ascii=False) if year_list else None,
            len(year_list),
            len(linked_payments.get(patient_id, set())),
            len(linked_appointments.get(patient_id, set())),
            anchor_match_count[patient_id],
            mn, mx,
        ))
    conn.commit()


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
    build_anchors_and_evidence(conn)
    n = conn.execute("SELECT COUNT(*) FROM identity_anchor_patients_phase3").fetchone()[0]
    print(f"Anchor patients: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
