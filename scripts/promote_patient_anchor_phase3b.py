# -*- coding: utf-8 -*-
"""
Phase 3B: Score patient-anchor candidates, apply dominance, promote only safe links.
Target: PATIENT RECOVERY. Does NOT update patients or payments.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"

# Patient-recovery scoring weights
SCORE_RECORD_NO_EXACT = 90
SCORE_PHONE_EXACT = 70
SCORE_EXACT_NAME = 35
SCORE_HIGH_NAME_SIM = 20
SCORE_REPEATED_CLUSTER_PHONE = 25
SCORE_REPEATED_CLUSTER_RECORDNO = 35

# Exact name alone => reject (no promotion)
# Phone alone => review only
PENALTY_NAME_ONLY = -100
PENALTY_PHONE_ONLY_FOR_PROMOTE = 0   # we set confidence to REVIEW, not REJECT

DOMINANCE_MARGIN = 15


def run_schema(conn) -> None:
    for name in (
        "006_phase3b_anchored_patient_expansion_schema.sql",
        "007_phase3b_anchored_patient_expansion_indexes.sql",
    ):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _score_row(row: tuple) -> float:
    """(phone_match, record_no_match, exact_name, high_name_sim, repeated_phone, repeated_recordno) -> score."""
    ph, rec, exact_n, high_n, rep_ph, rep_rec = row[0], row[1], row[2], row[3], row[4], row[5]
    s = 0.0
    if rec:
        s += SCORE_RECORD_NO_EXACT
    if ph:
        s += SCORE_PHONE_EXACT
    if exact_n:
        s += SCORE_EXACT_NAME
    if high_n:
        s += SCORE_HIGH_NAME_SIM
    if rep_ph:
        s += SCORE_REPEATED_CLUSTER_PHONE
    if rep_rec:
        s += SCORE_REPEATED_CLUSTER_RECORDNO
    # Exact name alone (no phone, no record_no) => reject
    if exact_n and not ph and not rec:
        s += PENALTY_NAME_ONLY
    return round(s, 2)


def _should_promote(ph: int, rec: int, exact_n: int, high_n: int, rep_ph: int, rep_rec: int) -> bool:
    """True only for safe promotion rules."""
    if exact_n and not ph and not rec:
        return False
    if ph and exact_n:
        return True
    if rec and (exact_n or high_n or ph):
        return True
    if rec and not ph and not exact_n and not high_n:
        return True
    if rep_ph and exact_n:
        return True
    if rep_rec and (exact_n or high_n):
        return True
    if ph and high_n:
        return True
    return False


def _confidence(score: float, ph: int, rec: int, exact_n: int, high_n: int, rep_ph: int, rep_rec: int) -> str:
    if score < 0:
        return "REJECT"
    if exact_n and not ph and not rec:
        return "REJECT"
    if _should_promote(ph, rec, exact_n, high_n, rep_ph, rep_rec):
        return "PROMOTE"
    if ph and not exact_n and not high_n:
        return "REVIEW"
    if score >= 40:
        return "REVIEW"
    return "REJECT"


def score_and_promote(conn) -> None:
    conn.execute("DELETE FROM patient_anchor_promoted_phase3b")
    conn.commit()

    rows = conn.execute("""
        SELECT candidate_id, unrecovered_patient_id, anchor_patient_id,
               phone_match_flag, record_no_match_flag, exact_name_match_flag, high_name_similarity_flag,
               repeated_cluster_phone_flag, repeated_cluster_recordno_flag, support_signal_count, candidate_rule
        FROM patient_anchor_candidates_phase3b
    """).fetchall()

    for r in rows:
        cid, ur_id, anchor_id, ph, rec, exact_n, high_n, rep_ph, rep_rec, support, rule = r
        score = _score_row((ph, rec, exact_n, high_n, rep_ph, rep_rec))
        conf = _confidence(score, ph, rec, exact_n, high_n, rep_ph, rep_rec)
        conn.execute(
            "UPDATE patient_anchor_candidates_phase3b SET score_raw = ?, confidence_level = ? WHERE candidate_id = ?",
            (score, conf, cid),
        )
    conn.commit()

    by_unrecovered = defaultdict(list)
    for r in conn.execute("""
        SELECT candidate_id, unrecovered_patient_id, anchor_patient_id, score_raw, candidate_rule, support_signal_count, confidence_level
        FROM patient_anchor_candidates_phase3b WHERE confidence_level = 'PROMOTE'
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
            "UPDATE patient_anchor_candidates_phase3b SET match_status = 'ambiguous' WHERE candidate_id = ?",
            (cid,),
        )
    conn.commit()

    ins = """
        INSERT INTO patient_anchor_promoted_phase3b
        (unrecovered_patient_id, anchor_patient_id, candidate_rule, support_signal_count, score_raw, confidence_level, promotion_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    for ur_id, cands in by_unrecovered.items():
        cands = [c for c in cands if c[2] not in ambiguous_cids]
        if not cands:
            continue
        if len(cands) == 1:
            anchor_id, score, _, rule, support, conf = cands[0]
            conn.execute(ins, (ur_id, anchor_id, rule or "P3B_multi_signal", support, score, conf, "unique_anchor"))
            continue
        scores = [c[1] for c in cands]
        best = max(scores)
        other = [c[1] for c in cands if c[1] != best]
        second = max(other) if other else best
        if (best - second) >= DOMINANCE_MARGIN:
            best_c = [c for c in cands if c[1] == best][0]
            conn.execute(ins, (ur_id, best_c[0], best_c[3] or "P3B", best_c[4], best_c[1], best_c[5], "dominant_anchor"))
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
    n = conn.execute("SELECT COUNT(*) FROM patient_anchor_promoted_phase3b").fetchone()[0]
    print(f"Promoted patient-anchor links: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
</think>
Fixing the promotion logic and implementing it cleanly.
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
StrReplace