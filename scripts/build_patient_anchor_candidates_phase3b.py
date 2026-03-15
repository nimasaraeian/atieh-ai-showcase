# -*- coding: utf-8 -*-
"""
Phase 3B: Build unrecovered_patients_phase3b and patient_anchor_candidates_phase3b.
Unrecovered = patients in patients_identity_normalized not in identity_anchor_patients_phase3.
Candidates = (unrecovered_patient_id, anchor_patient_id) with evidence flags.
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
sys.path.insert(0, str(REPO))

from scripts.helpers.name_cleanup import name_similarity_score
from scripts.helpers.phase3_cluster_logic import (
    repeated_cluster_phone,
    repeated_cluster_recordno,
    high_name_similarity_threshold,
)

HIGH_NAME_SIM = 85.0


def run_schema(conn) -> None:
    for name in (
        "006_phase3b_anchored_patient_expansion_schema.sql",
        "007_phase3b_anchored_patient_expansion_indexes.sql",
    ):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def build_unrecovered(conn) -> int:
    conn.execute("DELETE FROM unrecovered_patients_phase3b")
    conn.commit()
    conn.execute("""
        INSERT INTO unrecovered_patients_phase3b (patient_id, patient_name_key, patient_name_norm, phone_primary_norm, record_no_norm)
        SELECT p.patient_id, p.patient_name_key, p.patient_name_norm, p.phone_primary_norm, p.record_no_norm
        FROM patients_identity_normalized p
        WHERE p.patient_id NOT IN (SELECT patient_id FROM identity_anchor_patients_phase3)
    """)
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM unrecovered_patients_phase3b").fetchone()[0]


def _anchor_phones(conn) -> dict:
    """phone_norm -> [(anchor_patient_id, observation_count), ...]"""
    rows = conn.execute("""
        SELECT patient_id, phone_norm, observation_count FROM identity_anchor_phone_phase3
    """).fetchall()
    out = defaultdict(list)
    for r in rows:
        out[r[1]].append((r[0], r[2]))
    return dict(out)


def _anchor_recordnos(conn) -> dict:
    """record_no_norm -> [(anchor_patient_id, observation_count), ...]"""
    rows = conn.execute("""
        SELECT patient_id, record_no_norm, observation_count FROM identity_anchor_recordno_phase3
    """).fetchall()
    out = defaultdict(list)
    for r in rows:
        if r[1]:
            out[r[1]].append((r[0], r[2]))
    return dict(out)


def _anchor_names(conn) -> dict:
    """patient_name_key -> [anchor_patient_id, ...]"""
    rows = conn.execute("""
        SELECT patient_id, patient_name_key FROM identity_anchor_name_phase3
    """).fetchall()
    out = defaultdict(list)
    for r in rows:
        if r[1]:
            out[r[1]].append(r[0])
    return dict(out)


def _anchor_name_norms(conn) -> dict:
    """anchor_patient_id -> list of patient_name_norm"""
    rows = conn.execute("SELECT patient_id, patient_name_norm FROM identity_anchor_name_phase3 WHERE patient_name_norm IS NOT NULL").fetchall()
    out = defaultdict(list)
    for r in rows:
        out[r[0]].append(r[1])
    return dict(out)


def _assign_rule(flags: dict, support: int) -> str | None:
    if flags.get("record_no_match") and (flags.get("exact_name_match") or flags.get("high_name_similarity") or flags.get("phone_match")):
        return "P3B_record_no_plus_name_or_phone"
    if flags.get("record_no_match") and support >= 1:
        return "P3B_record_no_alone"
    if flags.get("phone_match") and flags.get("exact_name_match"):
        return "P3B_phone_exact_name"
    if flags.get("repeated_cluster_phone") and flags.get("exact_name_match"):
        return "P3B_repeated_cluster_phone_exact_name"
    if flags.get("repeated_cluster_recordno") and (flags.get("exact_name_match") or flags.get("high_name_similarity")):
        return "P3B_repeated_cluster_recordno_name"
    if flags.get("phone_match") and flags.get("high_name_similarity"):
        return "P3B_phone_high_name_sim"
    if flags.get("phone_match"):
        return "P3B_phone_only"
    if flags.get("exact_name_match") and support >= 2:
        return "P3B_exact_name_plus_support"
    if support >= 2:
        return "P3B_multi_signal"
    return None


def build_candidates(conn) -> int:
    conn.execute("DELETE FROM patient_anchor_candidates_phase3b")
    conn.commit()

    anchor_phones = _anchor_phones(conn)
    anchor_recordnos = _anchor_recordnos(conn)
    anchor_names = _anchor_names(conn)
    anchor_name_norms = _anchor_name_norms(conn)
    anchor_set = set(conn.execute("SELECT patient_id FROM identity_anchor_patients_phase3").fetchall())
    anchor_set = {r[0] for r in anchor_set}

    unrecovered = conn.execute("""
        SELECT patient_id, patient_name_key, patient_name_norm, phone_primary_norm, record_no_norm
        FROM unrecovered_patients_phase3b
    """).fetchall()

    ins = """
        INSERT INTO patient_anchor_candidates_phase3b (
            unrecovered_patient_id, anchor_patient_id,
            phone_match_flag, record_no_match_flag, exact_name_match_flag, high_name_similarity_flag,
            repeated_cluster_phone_flag, repeated_cluster_recordno_flag, support_signal_count,
            candidate_rule, match_status, diagnostics_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?, 'candidate', ?)
    """
    count = 0
    for ur in unrecovered:
        ur_id, name_key, name_norm, phone, record_no = ur
        target_anchors = set()
        if phone and phone in anchor_phones:
            for (aid, _) in anchor_phones[phone]:
                target_anchors.add(aid)
        if record_no and record_no in anchor_recordnos:
            for (aid, _) in anchor_recordnos[record_no]:
                target_anchors.add(aid)
        if name_key and name_key in anchor_names:
            for aid in anchor_names[name_key]:
                target_anchors.add(aid)
        target_anchors &= anchor_set
        if not target_anchors:
            continue

        for anchor_id in target_anchors:
            flags = {
                "phone_match": False,
                "record_no_match": False,
                "exact_name_match": False,
                "high_name_similarity": False,
                "repeated_cluster_phone": False,
                "repeated_cluster_recordno": False,
            }
            if phone and phone in anchor_phones:
                for (aid, obs) in anchor_phones[phone]:
                    if aid == anchor_id:
                        flags["phone_match"] = True
                        flags["repeated_cluster_phone"] = repeated_cluster_phone(obs)
                        break
            if record_no and record_no in anchor_recordnos:
                for (aid, obs) in anchor_recordnos[record_no]:
                    if aid == anchor_id:
                        flags["record_no_match"] = True
                        flags["repeated_cluster_recordno"] = repeated_cluster_recordno(obs)
                        break
            if name_key and name_key in anchor_names and anchor_id in anchor_names[name_key]:
                flags["exact_name_match"] = True
            if name_norm and not flags["exact_name_match"] and anchor_id in anchor_name_norms:
                for an in anchor_name_norms[anchor_id]:
                    if high_name_similarity_threshold(name_similarity_score(name_norm, an)):
                        flags["high_name_similarity"] = True
                        break
            support = sum(1 for v in flags.values() if v)
            rule = _assign_rule(flags, support)
            conn.execute(ins, (
                ur_id, anchor_id,
                int(flags["phone_match"]), int(flags["record_no_match"]), int(flags["exact_name_match"]),
                int(flags["high_name_similarity"]), int(flags["repeated_cluster_phone"]), int(flags["repeated_cluster_recordno"]),
                support, rule, json.dumps(flags, ensure_ascii=False),
            ))
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
    n_unrec = build_unrecovered(conn)
    print(f"Unrecovered patients: {n_unrec}")
    n_cand = build_candidates(conn)
    print(f"Patient-anchor candidates: {n_cand}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
