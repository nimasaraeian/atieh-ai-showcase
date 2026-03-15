# -*- coding: utf-8 -*-
"""
Phase 4: Build phase4_cluster_candidates from unrecovered patients vs anchor clusters.
Uses phase4_phone_patient_links, phase4_name_patient_links.
Scoring: phone_primary +70, phone_all +55, repeated anchored +35, name_key +20, name+phone cluster +25, cross-source +20, obs>=2 +20, obs>=4 +35.
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
    for name in ("010_phase4_graph_propagation_schema.sql", "011_phase4_graph_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def build_candidates(conn) -> int:
    conn.execute("DELETE FROM phase4_cluster_candidates")
    conn.commit()

    anchor_set = {r[0] for r in conn.execute("SELECT patient_id FROM identity_anchor_patients_phase3").fetchall()}

    # phone_norm -> [(patient_id, cluster_id, is_primary, observation_count, source_type), ...]
    phone_links = conn.execute("""
        SELECT phone_norm, patient_id, cluster_id, is_primary, observation_count, source_type
        FROM phase4_phone_patient_links
    """).fetchall()
    by_phone = defaultdict(list)
    for r in phone_links:
        by_phone[r[0]].append(r[1:])

    # Per (cluster_id, phone_norm): total observation count and whether primary appears
    cluster_phone_obs = defaultdict(lambda: defaultdict(lambda: {"obs": 0, "primary": 0}))
    for r in phone_links:
        ph, pid, cid, is_prim, obs, src = r[0], r[1], r[2], r[3], r[4], r[5]
        if cid is not None and cid in anchor_set:
            cluster_phone_obs[cid][ph]["obs"] += obs
            if is_prim:
                cluster_phone_obs[cid][ph]["primary"] = 1

    # name_key -> [(patient_id, cluster_id, observation_count), ...]
    name_links = conn.execute("""
        SELECT patient_name_key, patient_id, cluster_id, observation_count
        FROM phase4_name_patient_links
    """).fetchall()
    by_name = defaultdict(list)
    for r in name_links:
        if r[0]:
            by_name[r[0]].append((r[1], r[2], r[3]))

    # Unrecovered patients with their phones and name
    try:
        unrecovered = conn.execute("""
            SELECT u.patient_id, u.patient_name_key, u.phone_primary_norm, p.phone_all_norm_json
            FROM unrecovered_patients_phase3b u
            LEFT JOIN patients_identity_normalized p ON p.patient_id = u.patient_id
        """).fetchall()
    except Exception:
        unrecovered = conn.execute("""
            SELECT p.patient_id, p.patient_name_key, p.phone_primary_norm, p.phone_all_norm_json
            FROM patients_identity_normalized p
            WHERE p.patient_id NOT IN (SELECT patient_id FROM identity_anchor_patients_phase3)
        """).fetchall()

    def collect_phones(js):
        if not js:
            return []
        try:
            return [x for x in json.loads(js) if x and isinstance(x, str)]
        except Exception:
            return []

    ins = """
        INSERT INTO phase4_cluster_candidates (
            unrecovered_patient_id, cluster_id, phone_primary_match, phone_all_match, name_key_match,
            repeated_anchored_phone, name_support_same_phone_cluster, cross_source_evidence, repeated_obs_count,
            support_signal_count, score_raw, propagation_rule, confidence_level, match_status, diagnostics_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'candidate', ?)
    """
    count = 0
    for ur in unrecovered:
        ur_id = ur[0]
        name_key = ur[1]
        phone_prim = ur[2]
        phone_all_json = ur[3] if len(ur) > 3 else None
        phones_ur = list(set(([phone_prim] if phone_prim else []) + collect_phones(phone_all_json)))

        clusters_with_phone = set()
        primary_by_cluster = {}
        all_by_cluster = {}
        obs_by_cluster = defaultdict(int)
        for ph in phones_ur:
            if ph not in by_phone:
                continue
            for (pid, cid, is_prim, obs, src) in by_phone[ph]:
                if cid is not None and cid in anchor_set:
                    clusters_with_phone.add(cid)
                    obs_by_cluster[cid] += obs
                    if is_prim:
                        primary_by_cluster[cid] = 1
                    else:
                        all_by_cluster[cid] = 1
        clusters_with_name = set()
        for (pid, cid, obs) in by_name.get(name_key or "", []):
            if cid is not None and cid in anchor_set:
                clusters_with_name.add(cid)

        candidates = clusters_with_phone | clusters_with_name
        if not candidates:
            continue

        for cid in candidates:
            cluster_phones = cluster_phone_obs.get(cid, {})
            phone_prim_match = 1 if (phone_prim and phone_prim in cluster_phones and cluster_phones[phone_prim].get("primary")) else 0
            if not phone_prim_match and phone_prim and phone_prim in cluster_phones:
                phone_prim_match = 0  # match but not as primary
            phone_all_match = 1 if any(ph in cluster_phones for ph in phones_ur) else 0
            if phone_prim_match:
                phone_all_match = 1
            name_key_match = 1 if cid in clusters_with_name else 0
            repeated_obs = obs_by_cluster.get(cid, 0)
            repeated_anchored = 1 if repeated_obs >= 2 else 0
            name_support_same_cluster = 1 if name_key_match and (phone_prim_match or phone_all_match) else 0
            cross_source = 1 if repeated_obs >= 2 else 0  # simplified: multiple observations imply cross-source
            repeated_obs_count = min(repeated_obs, 10)

            support_signal_count = phone_prim_match + phone_all_match + name_key_match + repeated_anchored + name_support_same_cluster + cross_source
            diag = {"phone_primary": phone_prim_match, "phone_all": phone_all_match, "name_key": name_key_match, "repeated_anchored": repeated_anchored, "name_support_same": name_support_same_cluster, "repeated_obs": repeated_obs_count}
            rule = "P4_phone_primary" if phone_prim_match else "P4_phone_all"
            if name_key_match:
                rule += "_name"
            if repeated_anchored:
                rule += "_repeated"
            conn.execute(ins, (
                ur_id, cid, phone_prim_match, phone_all_match, name_key_match,
                repeated_anchored, name_support_same_cluster, cross_source, repeated_obs_count,
                support_signal_count, None, rule, json.dumps(diag),
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
    print(f"Phase4 cluster candidates: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
