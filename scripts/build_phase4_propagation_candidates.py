# -*- coding: utf-8 -*-
"""
Phase 4: Build propagation candidates: unrecovered patients vs expanded cluster evidence.
Uses phone_primary_norm, phone_all_norm_json, patient_name_key. Repeated/shared signals.
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
from scripts.helpers.phase3_cluster_logic import high_name_similarity_threshold

HIGH_NAME_SIM = 85.0


def _collect_phones(s: str | None) -> list[str]:
    if not s:
        return []
    try:
        out = json.loads(s)
        return [x for x in out if x and isinstance(x, str)]
    except Exception:
        return []


def run_schema(conn) -> None:
    for name in ("008_phase4_multihop_propagation_schema.sql", "009_phase4_multihop_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def build_candidates(conn) -> int:
    conn.execute("DELETE FROM identity_phase4_candidates")
    conn.commit()

    # Evidence: (type, value) -> [(cluster_id, observation_count in that cluster), ...]
    rows = conn.execute("""
        SELECT cluster_id, evidence_type, evidence_value,
               COUNT(*) AS observation_count
        FROM identity_cluster_evidence_phase4
        GROUP BY cluster_id, evidence_type, evidence_value
    """).fetchall()

    # value -> list of (cluster_id, obs_count) for repeated-in-cluster
    evidence_phone = defaultdict(list)
    evidence_name = defaultdict(list)
    evidence_recordno = defaultdict(list)
    for r in rows:
        cluster_id, etype, value, obs = r
        if not value:
            continue
        if etype == "phone":
            evidence_phone[value].append((cluster_id, obs))
        elif etype == "name_key":
            evidence_name[value].append((cluster_id, obs))
        elif etype == "record_no":
            evidence_recordno[value].append((cluster_id, obs))

    # Shared phone across clusters: phone -> number of distinct clusters
    phone_cluster_count = {ph: len(set(c for c, _ in lst)) for ph, lst in evidence_phone.items()}

    # Unrecovered: patient_id + identity fields; include phone_all_norm_json from patients_identity_normalized
    try:
        unrecovered = conn.execute("""
            SELECT u.patient_id, u.patient_name_key, u.patient_name_norm, u.phone_primary_norm, u.record_no_norm,
                   p.phone_all_norm_json
            FROM unrecovered_patients_phase3b u
            LEFT JOIN patients_identity_normalized p ON p.patient_id = u.patient_id
        """).fetchall()
    except Exception:
        unrecovered = conn.execute("""
            SELECT p.patient_id, p.patient_name_key, p.patient_name_norm, p.phone_primary_norm, p.record_no_norm,
                   p.phone_all_norm_json
            FROM patients_identity_normalized p
            WHERE p.patient_id NOT IN (SELECT patient_id FROM identity_anchor_patients_phase3)
        """).fetchall()

    # Anchor name norms for high_name_sim: cluster_id -> list of name_norm from evidence (we don't have norm in evidence; use anchor name table)
    anchor_name_norms = defaultdict(list)
    for r in conn.execute("""
        SELECT patient_id, patient_name_norm FROM identity_anchor_name_phase3 WHERE patient_name_norm IS NOT NULL
    """).fetchall():
        anchor_name_norms[r[0]].append(r[1])

    ins = """
        INSERT INTO identity_phase4_candidates (
            unrecovered_patient_id, cluster_id, phone_match_flag, name_key_match_flag, record_no_match_flag,
            high_name_sim_flag, repeated_in_cluster_phone, repeated_in_cluster_name, repeated_in_cluster_recordno,
            shared_phone_across_clusters, support_signal_count, propagation_rule, match_status, diagnostics_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'candidate', ?)
    """
    count = 0
    for ur in unrecovered:
        if len(ur) >= 6:
            ur_id, name_key, name_norm, phone_prim, record_no, phone_all_json = ur
        else:
            ur_id, name_key, name_norm, phone_prim, record_no = ur
            phone_all_json = None
        phones_ur = list(set(([phone_prim] if phone_prim else []) + _collect_phones(phone_all_json)))

        clusters_found = set()
        for ph in phones_ur:
            if ph in evidence_phone:
                for (cluster_id, obs) in evidence_phone[ph]:
                    clusters_found.add((cluster_id, "phone", obs, ph))
        if name_key and name_key in evidence_name:
            for (cluster_id, obs) in evidence_name[name_key]:
                clusters_found.add((cluster_id, "name_key", obs, None))
        if record_no and record_no in evidence_recordno:
            for (cluster_id, obs) in evidence_recordno[record_no]:
                clusters_found.add((cluster_id, "record_no", obs, None))

        # Group by cluster_id
        by_cluster = defaultdict(lambda: {"phone": False, "name_key": False, "record_no": False, "phone_obs": 0, "name_obs": 0, "rec_obs": 0, "phone_val": None})
        for item in clusters_found:
            cluster_id, etype, obs, ph_val = item
            if etype == "phone":
                by_cluster[cluster_id]["phone"] = True
                by_cluster[cluster_id]["phone_obs"] = max(by_cluster[cluster_id]["phone_obs"], obs)
                by_cluster[cluster_id]["phone_val"] = ph_val
            elif etype == "name_key":
                by_cluster[cluster_id]["name_key"] = True
                by_cluster[cluster_id]["name_obs"] = max(by_cluster[cluster_id]["name_obs"], obs)
            elif etype == "record_no":
                by_cluster[cluster_id]["record_no"] = True
                by_cluster[cluster_id]["rec_obs"] = max(by_cluster[cluster_id]["rec_obs"], obs)

        for cluster_id, data in by_cluster.items():
            ph = data["phone"]
            name_k = data["name_key"]
            rec = data["record_no"]
            phone_obs = data["phone_obs"]
            name_obs = data["name_obs"]
            rec_obs = data["rec_obs"]
            repeated_phone = 1 if phone_obs >= 2 else 0
            repeated_name = 1 if name_obs >= 2 else 0
            repeated_rec = 1 if rec_obs >= 2 else 0
            shared_phone = 0
            if data["phone_val"] and data["phone_val"] in phone_cluster_count:
                if phone_cluster_count[data["phone_val"]] > 1:
                    shared_phone = 1
            high_sim = 0
            if name_norm and cluster_id in anchor_name_norms:
                for an in anchor_name_norms[cluster_id]:
                    if high_name_similarity_threshold(name_similarity_score(name_norm, an)):
                        high_sim = 1
                        break
            support = sum([ph, name_k, rec, high_sim])
            rule = "P4_phone" if ph else None
            if name_k:
                rule = "P4_name_key" if not rule else "P4_phone_name"
            if rec:
                rule = "P4_record_no" if not rule else (rule or "") + "_record_no"
            if repeated_phone and ph:
                rule = (rule or "P4") + "_repeated_phone"
            if repeated_name and name_k:
                rule = (rule or "P4") + "_repeated_name"
            diag = json.dumps({"phone": ph, "name_key": name_k, "record_no": rec, "repeated_phone": repeated_phone, "repeated_name": repeated_name, "shared_phone": shared_phone}, ensure_ascii=False)
            conn.execute(ins, (
                ur_id, cluster_id, int(ph), int(name_k), int(rec), int(high_sim),
                repeated_phone, repeated_name, repeated_rec, shared_phone, support, rule, diag,
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
    print(f"Phase4 propagation candidates: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
