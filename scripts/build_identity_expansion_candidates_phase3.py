# -*- coding: utf-8 -*-
"""
Phase 3: Generate expansion candidates from non-promoted payment/appointment rows to anchor patients.
Populates identity_expansion_candidates_phase3. Does NOT promote; promotion is a separate step.
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
    date_compatible,
)

HIGH_NAME_SIM_THRESHOLD = 85.0


def run_schema(conn) -> None:
    for name in ("004_phase3_graph_expansion_schema.sql", "005_phase3_graph_expansion_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _already_promoted(conn) -> tuple[set, set]:
    """Return (set of payments_staging_id, set of appointment_staging_id) already in phase2 safe."""
    rows = conn.execute("""
        SELECT left_source_type, left_row_id FROM safe_identity_matches_phase2
    """).fetchall()
    pay_ids = {r[1] for r in rows if r[0] == "payment"}
    app_ids = {r[1] for r in rows if r[0] == "appointment"}
    return pay_ids, app_ids


def _anchor_phones(conn) -> dict[str, list[tuple[int, int]]]:
    """phone_norm -> [(patient_id, observation_count), ...]"""
    rows = conn.execute("""
        SELECT patient_id, phone_norm, observation_count FROM identity_anchor_phone_phase3
    """).fetchall()
    out = defaultdict(list)
    for r in rows:
        out[r[1]].append((r[0], r[2]))
    return dict(out)


def _anchor_recordnos(conn) -> dict[str, list[tuple[int, int]]]:
    """record_no_norm -> [(patient_id, observation_count), ...]"""
    rows = conn.execute("""
        SELECT patient_id, record_no_norm, observation_count FROM identity_anchor_recordno_phase3
    """).fetchall()
    out = defaultdict(list)
    for r in rows:
        if r[1]:
            out[r[1]].append((r[0], r[2]))
    return dict(out)


def _anchor_names(conn) -> dict[str, list[int]]:
    """patient_name_key -> [patient_id, ...]"""
    rows = conn.execute("""
        SELECT patient_id, patient_name_key FROM identity_anchor_name_phase3
    """).fetchall()
    out = defaultdict(list)
    for r in rows:
        if r[1]:
            out[r[1]].append(r[0])
    return dict(out)


def _anchor_profiles(conn) -> dict[int, tuple[set, str | None, str | None]]:
    """patient_id -> (years_set, min_date_norm, max_date_norm)"""
    rows = conn.execute("""
        SELECT patient_id, years_json, min_date_norm, max_date_norm
        FROM identity_anchor_profile_phase3
    """).fetchall()
    out = {}
    for r in rows:
        years = set()
        if r[1]:
            try:
                years = set(json.loads(r[1]))
            except Exception:
                pass
        out[r[0]] = (years, r[2], r[3])
    return out


def _assign_rule(flags: dict, support_count: int) -> str | None:
    """First matching rule P1..P6."""
    if flags.get("record_no_match") and (
        flags.get("exact_name_match") or flags.get("high_name_similarity") or flags.get("phone_match")
    ):
        return "P1_strong_record_no_expansion"
    if flags.get("phone_match") and flags.get("repeated_cluster_phone") and (
        flags.get("exact_name_match") or flags.get("high_name_similarity")
        or flags.get("same_year") or flags.get("date_compatible")
    ):
        return "P2_repeated_anchored_phone_expansion"
    if flags.get("exact_name_match") and flags.get("record_no_match") and flags.get("same_year"):
        return "P3_exact_name_recordno_year"
    if flags.get("phone_match") and flags.get("exact_name_match"):
        return "P4_phone_exact_name_inside_cluster"
    if flags.get("phone_match") and flags.get("high_name_similarity") and flags.get("repeated_cluster_phone"):
        return "P5_phone_high_sim_repeated_phone"
    if support_count >= 2:
        return "P6_multi_signal_cluster_support"
    return None


def _candidates_for_row(
    conn,
    source_type: str,
    source_row_id: int,
    target_patient_ids: set[int],
    phone_norm: str | None,
    record_no_norm: str | None,
    name_key: str | None,
    name_norm: str | None,
    year: int | None,
    date_norm: str | None,
    anchor_phones: dict,
    anchor_recordnos: dict,
    anchor_names: dict,
    profiles: dict,
    anchor_name_norms: dict[int, str],
) -> list[tuple]:
    """Produce candidate rows (target_patient_id, flags, support_count, rule)."""
    rows_out = []
    for pid in target_patient_ids:
        flags = {
            "phone_match": False,
            "record_no_match": False,
            "exact_name_match": False,
            "high_name_similarity": False,
            "same_year": False,
            "date_compatible": False,
            "repeated_cluster_phone": False,
            "repeated_cluster_recordno": False,
        }
        if phone_norm and phone_norm in anchor_phones:
            for (aid, obs) in anchor_phones[phone_norm]:
                if aid == pid:
                    flags["phone_match"] = True
                    flags["repeated_cluster_phone"] = repeated_cluster_phone(obs)
                    break
        if record_no_norm and record_no_norm in anchor_recordnos:
            for (aid, obs) in anchor_recordnos[record_no_norm]:
                if aid == pid:
                    flags["record_no_match"] = True
                    flags["repeated_cluster_recordno"] = repeated_cluster_recordno(obs)
                    break
        if name_key and name_key in anchor_names:
            if pid in anchor_names[name_key]:
                flags["exact_name_match"] = True
        if name_norm and not flags["exact_name_match"] and pid in anchor_name_norms:
            for an in anchor_name_norms[pid]:
                if high_name_similarity_threshold(name_similarity_score(name_norm, an)):
                    flags["high_name_similarity"] = True
                    break
        prof = profiles.get(pid)
        if prof:
            years_set, min_d, max_d = prof
            if year is not None and year in years_set:
                flags["same_year"] = True
            if date_norm and (min_d or max_d):
                flags["date_compatible"] = date_compatible(date_norm, min_d) or date_compatible(date_norm, max_d)
        support_count = sum(1 for v in flags.values() if v)
        rule = _assign_rule(flags, support_count)
        rows_out.append((pid, flags, support_count, rule))
    return rows_out


def build_candidates(conn) -> int:
    conn.execute("DELETE FROM identity_expansion_candidates_phase3")
    conn.commit()

    promoted_pay, promoted_app = _already_promoted(conn)
    anchor_phones = _anchor_phones(conn)
    anchor_recordnos = _anchor_recordnos(conn)
    anchor_names = _anchor_names(conn)
    profiles = _anchor_profiles(conn)
    anchor_set = set(profiles.keys())
    anchor_name_norms = defaultdict(list)
    for row in conn.execute("SELECT patient_id, patient_name_norm FROM identity_anchor_name_phase3").fetchall():
        if row[1]:
            anchor_name_norms[row[0]].append(row[1])

    ins = """
        INSERT INTO identity_expansion_candidates_phase3 (
            source_type, source_row_id, target_patient_id,
            phone_match_flag, record_no_match_flag, exact_name_match_flag, high_name_similarity_flag,
            same_year_flag, date_compatible_flag, repeated_cluster_phone_flag, repeated_cluster_recordno_flag,
            support_signal_count, expansion_rule, match_status, diagnostics_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'candidate', ?)
    """
    count = 0

    # Eligible payments
    pay_rows = conn.execute("""
        SELECT payments_staging_id, mobile_primary_norm, record_no_norm, patient_name_key, patient_name_norm,
               shamsi_year, admission_date_norm
        FROM identity_normalized_payments
    """).fetchall()
    for r in pay_rows:
        staging_id, phone, rec_no, name_k, name_n, year, date_n = r
        if staging_id in promoted_pay:
            continue
        target_ids = set()
        if phone and phone in anchor_phones:
            for (pid, _) in anchor_phones[phone]:
                target_ids.add(pid)
        if rec_no and rec_no in anchor_recordnos:
            for (pid, _) in anchor_recordnos[rec_no]:
                target_ids.add(pid)
        if name_k and name_k in anchor_names:
            for pid in anchor_names[name_k]:
                target_ids.add(pid)
        target_ids &= anchor_set
        if not target_ids:
            continue
        for pid, flags, support_count, rule in _candidates_for_row(
            conn, "payment", staging_id, target_ids,
            phone, rec_no, name_k, name_n, year, date_n,
            anchor_phones, anchor_recordnos, anchor_names, profiles, anchor_name_norms,
        ):
            conn.execute(ins, (
                "payment", staging_id, pid,
                int(flags["phone_match"]), int(flags["record_no_match"]), int(flags["exact_name_match"]),
                int(flags["high_name_similarity"]), int(flags["same_year"]), int(flags["date_compatible"]),
                int(flags["repeated_cluster_phone"]), int(flags["repeated_cluster_recordno"]),
                support_count, rule, json.dumps(flags, ensure_ascii=False),
            ))
            count += 1

    # Eligible appointments
    app_rows = conn.execute("""
        SELECT appointment_staging_id, phone_primary_norm, record_no_norm, patient_name_key, patient_name_norm,
               shamsi_year, appointment_date_norm
        FROM identity_normalized_appointments
    """).fetchall()
    for r in app_rows:
        staging_id, phone, rec_no, name_k, name_n, year, date_n = r
        if staging_id in promoted_app:
            continue
        target_ids = set()
        if phone and phone in anchor_phones:
            for (pid, _) in anchor_phones[phone]:
                target_ids.add(pid)
        if rec_no and rec_no in anchor_recordnos:
            for (pid, _) in anchor_recordnos[rec_no]:
                target_ids.add(pid)
        if name_k and name_k in anchor_names:
            for pid in anchor_names[name_k]:
                target_ids.add(pid)
        target_ids &= anchor_set
        if not target_ids:
            continue
        for pid, flags, support_count, rule in _candidates_for_row(
            conn, "appointment", staging_id, target_ids,
            phone, rec_no, name_k, name_n, year, date_n,
            anchor_phones, anchor_recordnos, anchor_names, profiles, anchor_name_norms,
        ):
            conn.execute(ins, (
                "appointment", staging_id, pid,
                int(flags["phone_match"]), int(flags["record_no_match"]), int(flags["exact_name_match"]),
                int(flags["high_name_similarity"]), int(flags["same_year"]), int(flags["date_compatible"]),
                int(flags["repeated_cluster_phone"]), int(flags["repeated_cluster_recordno"]),
                support_count, rule, json.dumps(flags, ensure_ascii=False),
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
    n = build_candidates(conn)
    print(f"Expansion candidates: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
