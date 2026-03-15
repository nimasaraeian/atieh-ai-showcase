# -*- coding: utf-8 -*-
"""
Phase 4: Score propagation candidates, apply dominance and shared-phone control, promote safe only.
Does NOT update patients or payments.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"

# Scoring: graph propagation
SCORE_PHONE = 70
SCORE_NAME_KEY = 35
SCORE_RECORD_NO = 90
SCORE_HIGH_NAME_SIM = 20
SCORE_REPEATED_IN_CLUSTER_PHONE = 25
SCORE_REPEATED_IN_CLUSTER_NAME = 20
SCORE_REPEATED_IN_CLUSTER_RECORDNO = 25
PENALTY_SHARED_PHONE_ACROSS_CLUSTERS = -40
PENALTY_NAME_ONLY = -100

DOMINANCE_MARGIN = 15


def run_schema(conn) -> None:
    for name in ("008_phase4_multihop_propagation_schema.sql", "009_phase4_multihop_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _score_row(row: tuple) -> float:
    (ph, name_k, rec, high_sim, rep_ph, rep_name, rep_rec, shared_ph) = row
    s = 0.0
    if ph:
        s += SCORE_PHONE
    if name_k:
        s += SCORE_NAME_KEY
    if rec:
        s += SCORE_RECORD_NO
    if high_sim:
        s += SCORE_HIGH_NAME_SIM
    if rep_ph:
        s += SCORE_REPEATED_IN_CLUSTER_PHONE
    if rep_name:
        s += SCORE_REPEATED_IN_CLUSTER_NAME
    if rep_rec:
        s += SCORE_REPEATED_IN_CLUSTER_RECORDNO
    if shared_ph:
        s += PENALTY_SHARED_PHONE_ACROSS_CLUSTERS
    if name_k and not ph and not rec:
        s += PENALTY_NAME_ONLY
    return round(s, 2)


def _should_promote(ph: int, name_k: int, rec: int, high_sim: int, rep_ph: int, rep_name: int, rep_rec: int, shared_ph: int) -> bool:
    if name_k and not ph and not rec:
        return False
    if shared_ph and not (rep_ph or rep_name):
        return False
    if ph and (name_k or high_sim or rep_ph):
        return True
    if rec and (name_k or high_sim or ph):
        return True
    if rep_ph and (name_k or high_sim):
        return True
    if rep_name and (ph or rec):
        return True
    if rep_rec and (name_k or ph):
        return True
    return False


def _confidence(score: float, ph: int, name_k: int, rec: int, high_sim: int, rep_ph: int, rep_name: int, rep_rec: int, shared_ph: int) -> str:
    if score < 0:
        return "REJECT"
    if name_k and not ph and not rec:
        return "REJECT"
    if _should_promote(ph, name_k, rec, high_sim, rep_ph, rep_name, rep_rec, shared_ph):
        return "PROMOTE"
    if score >= 50:
        return "REVIEW"
    return "REJECT"


def score_and_promote(conn) -> None:
    conn.execute("DELETE FROM identity_phase4_promoted")
    conn.commit()

    rows = conn.execute("""
        SELECT candidate_id, unrecovered_patient_id, cluster_id,
               phone_match_flag, name_key_match_flag, record_no_match_flag, high_name_sim_flag,
               repeated_in_cluster_phone, repeated_in_cluster_name, repeated_in_cluster_recordno,
               shared_phone_across_clusters, support_signal_count, propagation_rule
        FROM identity_phase4_candidates
    """).fetchall()

    for r in rows:
        cid, ur_id, cluster_id, ph, name_k, rec, high_sim, rep_ph, rep_name, rep_rec, shared_ph, support, rule = r
        score = _score_row((ph, name_k, rec, high_sim, rep_ph, rep_name, rep_rec, shared_ph))
        conf = _confidence(score, ph, name_k, rec, high_sim, rep_ph, rep_name, rep_rec, shared_ph)
        conn.execute(
            "UPDATE identity_phase4_candidates SET score_raw = ?, confidence_level = ? WHERE candidate_id = ?",
            (score, conf, cid),
        )
    conn.commit()

    by_unrecovered = defaultdict(list)
    for r in conn.execute("""
        SELECT candidate_id, unrecovered_patient_id, cluster_id, score_raw, propagation_rule, support_signal_count, confidence_level
        FROM identity_phase4_candidates WHERE confidence_level = 'PROMOTE'
    """).fetchall():
        by_unrecovered[r[1]].append((r[2], r[3], r[0], r[4], r[5], r[6]))

    ambiguous_cids = set()
    for ur_id, cands in by_unrecovered.items():
        if len(cands) <= 1:
            continue
        scores = [c[1] for c in cands]
        best = max(scores)
        other = [s for s in scores if s != best]
        second = max(other) if other else best
        if best - second < DOMINANCE_MARGIN:
            for c in cands:
                ambiguous_cids.add(c[2])

    for cid in ambiguous_cids:
        conn.execute(
            "UPDATE identity_phase4_candidates SET match_status = 'ambiguous' WHERE candidate_id = ?",
            (cid,),
        )
    conn.commit()

    ins = """
        INSERT INTO identity_phase4_promoted
        (unrecovered_patient_id, cluster_id, propagation_rule, support_signal_count, score_raw, confidence_level, promotion_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    for ur_id, cands in by_unrecovered.items():
        cands = [c for c in cands if c[2] not in ambiguous_cids]
        if not cands:
            continue
        if len(cands) == 1:
            cluster_id, score, _, rule, support, conf = cands[0]
            conn.execute(ins, (ur_id, cluster_id, rule or "P4_propagation", support, score, conf, "unique_cluster"))
            continue
        scores = [c[1] for c in cands]
        best = max(scores)
        other = [c[1] for c in cands if c[1] != best]
        second = max(other) if other else best
        if (best - second) >= DOMINANCE_MARGIN:
            best_c = [c for c in cands if c[1] == best][0]
            conn.execute(ins, (ur_id, best_c[0], best_c[4] or "P4", best_c[5], best_c[1], best_c[6], "dominant_cluster"))
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
    score_and_promote(conn)
    n = conn.execute("SELECT COUNT(*) FROM identity_phase4_promoted").fetchone()[0]
    print(f"Phase4 promoted: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
