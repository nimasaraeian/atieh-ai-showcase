# -*- coding: utf-8 -*-
"""
Phase 4: Score phase4_cluster_candidates, apply dominance (margin 15), promote safe only.
Populate phase4_cluster_promoted and phase4_ambiguity_review.
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

# Scoring (user-specified)
SCORE_PHONE_PRIMARY = 70
SCORE_PHONE_ALL = 55
SCORE_REPEATED_ANCHORED_PHONE = 35
SCORE_NAME_KEY = 20
SCORE_NAME_SUPPORT_SAME_PHONE_CLUSTER = 25
SCORE_CROSS_SOURCE = 20
SCORE_REPEATED_OBS_2 = 20
SCORE_REPEATED_OBS_4 = 35
PENALTY_NAME_ONLY = -100

DOMINANCE_MARGIN = 15


def run_schema(conn) -> None:
    for name in ("010_phase4_graph_propagation_schema.sql", "011_phase4_graph_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _score_row(row: tuple) -> float:
    (phone_prim, phone_all, name_k, repeated_ph, name_support, cross_src, repeated_obs) = row
    s = 0.0
    if phone_prim:
        s += SCORE_PHONE_PRIMARY
    elif phone_all:
        s += SCORE_PHONE_ALL
    if name_k:
        s += SCORE_NAME_KEY
    if repeated_ph:
        s += SCORE_REPEATED_ANCHORED_PHONE
    if name_support:
        s += SCORE_NAME_SUPPORT_SAME_PHONE_CLUSTER
    if cross_src:
        s += SCORE_CROSS_SOURCE
    if repeated_obs >= 4:
        s += SCORE_REPEATED_OBS_4
    elif repeated_obs >= 2:
        s += SCORE_REPEATED_OBS_2
    if name_k and not phone_prim and not phone_all:
        s += PENALTY_NAME_ONLY
    return round(s, 2)


def _should_promote(phone_prim: int, phone_all: int, name_k: int, repeated_ph: int, name_support: int, score: float) -> bool:
    if name_k and not phone_prim and not phone_all:
        return False
    if phone_prim and (name_k or name_support or repeated_ph):
        return True
    if phone_all and (name_k or name_support or repeated_ph):
        return True
    if score >= 70 and (phone_prim or phone_all) and (name_k or repeated_ph):
        return True
    return False


def _confidence(score: float, phone_prim: int, phone_all: int, name_k: int, repeated_ph: int, name_support: int) -> str:
    if score < 0:
        return "REJECT"
    if name_k and not phone_prim and not phone_all:
        return "REJECT"
    if _should_promote(phone_prim, phone_all, name_k, repeated_ph, name_support, score):
        return "PROMOTE"
    if (phone_prim or phone_all) and not name_k and not repeated_ph:
        return "REVIEW"
    if score >= 40:
        return "REVIEW"
    return "REJECT"


def score_and_promote(conn) -> None:
    conn.execute("DELETE FROM phase4_ambiguity_review")
    conn.execute("DELETE FROM phase4_cluster_promoted")
    conn.commit()

    rows = conn.execute("""
        SELECT candidate_id, unrecovered_patient_id, cluster_id,
               phone_primary_match, phone_all_match, name_key_match,
               repeated_anchored_phone, name_support_same_phone_cluster, cross_source_evidence, repeated_obs_count,
               propagation_rule
        FROM phase4_cluster_candidates
    """).fetchall()

    for r in rows:
        cid, ur_id, cid2, ph_prim, ph_all, name_k, rep_ph, name_sup, cross_src, rep_obs, rule = r
        score = _score_row((ph_prim, ph_all, name_k, rep_ph, name_sup, cross_src, rep_obs))
        conf = _confidence(score, ph_prim, ph_all, name_k, rep_ph, name_sup)
        conn.execute(
            "UPDATE phase4_cluster_candidates SET score_raw = ?, confidence_level = ? WHERE candidate_id = ?",
            (score, conf, cid),
        )
    conn.commit()

    by_unrecovered = defaultdict(list)
    for r in conn.execute("""
        SELECT candidate_id, unrecovered_patient_id, cluster_id, score_raw, propagation_rule,
               support_signal_count
        FROM phase4_cluster_candidates WHERE confidence_level = 'PROMOTE'
    """).fetchall():
        by_unrecovered[r[1]].append(r)

    ambiguous_cids = set()
    for ur_id, cands in by_unrecovered.items():
        if len(cands) <= 1:
            continue
        scores = [c[3] for c in cands]
        best = max(scores)
        other = [s for s in scores if s != best]
        second = max(other) if other else best
        if best - second < DOMINANCE_MARGIN:
            for c in cands:
                ambiguous_cids.add(c[0])
            cluster_ids = [c[2] for c in cands]
            scores_json = json.dumps([c[3] for c in cands])
            conn.execute("""
                INSERT INTO phase4_ambiguity_review (unrecovered_patient_id, candidate_cluster_ids, scores_json, best_score, second_best_score, margin, reason)
                VALUES (?, ?, ?, ?, ?, ?, 'competing_targets_margin_under_15')
            """, (ur_id, json.dumps(cluster_ids), scores_json, best, second, best - second))
    conn.commit()

    for cid in ambiguous_cids:
        conn.execute("UPDATE phase4_cluster_candidates SET match_status = 'ambiguous' WHERE candidate_id = ?", (cid,))
    conn.commit()

    ins = """
        INSERT INTO phase4_cluster_promoted (unrecovered_patient_id, cluster_id, propagation_rule, support_signal_count, score_raw, confidence_level, promotion_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    for ur_id, cands in by_unrecovered.items():
        cands = [c for c in cands if c[0] not in ambiguous_cids]
        if not cands:
            continue
        c = cands[0]
        support = c[5] if len(c) > 5 else 0
        if len(cands) == 1:
            conn.execute(ins, (ur_id, c[2], c[4] or "P4", support, c[3], "PROMOTE", "unique_cluster"))
            continue
        scores = [x[3] for x in cands]
        best = max(scores)
        other = [x[3] for x in cands if x[3] != best]
        second = max(other) if other else best
        if (best - second) >= DOMINANCE_MARGIN:
            best_c = [x for x in cands if x[3] == best][0]
            conn.execute(ins, (ur_id, best_c[2], best_c[4] or "P4", best_c[5] if len(best_c) > 5 else 0, best_c[3], "PROMOTE", "dominant_cluster"))
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
    n = conn.execute("SELECT COUNT(*) FROM phase4_cluster_promoted").fetchone()[0]
    amb = conn.execute("SELECT COUNT(*) FROM phase4_ambiguity_review").fetchone()[0]
    print(f"Phase4 promoted: {n}, ambiguity review: {amb}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
