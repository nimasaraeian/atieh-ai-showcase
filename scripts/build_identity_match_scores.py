# -*- coding: utf-8 -*-
"""
Score identity candidates and assign confidence tiers (A/B/C/D) and match_status.
Collision detection: same phone → multiple patients → ambiguous.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"

# Scoring (documented)
SCORE_NATIONAL_ID_EXACT = 100
SCORE_PHONE_EXACT = 70
SCORE_RECORD_NO_EXACT = 60
SCORE_EXACT_NAME_KEY = 50
SCORE_HIGH_NAME_SIM = 30
SCORE_SAME_YEAR = 5
SCORE_CLOSE_DATE = 10
PENALTY_CONFLICT_NAME_SAME_PHONE = -25
PENALTY_CONFLICT_PHONE_SAME_NAME = -20
PENALTY_WEAK_NAME_SIM = -30

# Tiers
TIER_A_MIN = 100
TIER_B_MIN = 75
TIER_B_MAX = 99
TIER_C_MIN = 50
TIER_C_MAX = 74
# Tier D: < 50 or ambiguous


def run_schema(conn) -> None:
    for name in ("001_identity_resolution_schema.sql", "002_identity_resolution_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def score_one(name_exact: int, name_sim: float | None, phone_exact: int, nid_exact: int, record_exact: int, same_year: int, date_prox: int) -> float:
    raw = 0.0
    if nid_exact:
        raw += SCORE_NATIONAL_ID_EXACT
    if phone_exact:
        raw += SCORE_PHONE_EXACT
    if record_exact:
        raw += SCORE_RECORD_NO_EXACT
    if name_exact:
        raw += SCORE_EXACT_NAME_KEY
    elif name_sim is not None and name_sim >= 85:
        raw += SCORE_HIGH_NAME_SIM
    elif name_sim is not None and name_sim < 50:
        raw += PENALTY_WEAK_NAME_SIM
    if same_year:
        raw += SCORE_SAME_YEAR
    if date_prox:
        raw += SCORE_CLOSE_DATE
    return round(raw, 2)


def tier_from_score(score: float | None) -> str:
    if score is None:
        return "D"
    if score >= TIER_A_MIN:
        return "A"
    if TIER_B_MIN <= score <= TIER_B_MAX:
        return "B"
    if TIER_C_MIN <= score <= TIER_C_MAX:
        return "C"
    return "D"


def update_scores_and_tiers(conn) -> None:
    """Compute score_raw and confidence_tier for all candidates."""
    rows = conn.execute("""
        SELECT candidate_id, name_exact_flag, name_similarity_score, phone_exact_flag,
               national_id_exact_flag, record_no_exact_flag, same_year_flag, date_proximity_flag
        FROM identity_candidate_matches
    """).fetchall()
    for r in rows:
        cid, ne, nsim, pe, nid, rec, sy, dp = r
        score = score_one(ne or 0, nsim, pe or 0, nid or 0, rec or 0, sy or 0, dp or 0)
        tier = tier_from_score(score)
        conn.execute(
            "UPDATE identity_candidate_matches SET score_raw = ?, confidence_tier = ? WHERE candidate_id = ?",
            (score, tier, cid),
        )
    conn.commit()


def detect_collisions(conn) -> None:
    """
    Mark ambiguous: same (left_type, left_row_id) with multiple right_row_id for same right_type.
    Or same phone mapping to multiple patients.
    """
    # Candidates that are payment↔patient or appointment↔patient: left (payment/appointment) -> right (patient)
    # If one left maps to multiple rights, mark those as ambiguous
    cur = conn.execute("""
        SELECT candidate_id, left_source_type, left_row_id, right_source_type, right_row_id
        FROM identity_candidate_matches
        WHERE right_source_type = 'patient'
    """)
    by_left = defaultdict(list)
    for r in cur.fetchall():
        cid, lt, lid, rt, rid = r
        by_left[(lt, lid)].append((cid, rid))

    ambiguous_ids = set()
    for (lt, lid), pairs in by_left.items():
        unique_rights = {r[1] for r in pairs}
        if len(unique_rights) > 1:
            for cid, _ in pairs:
                ambiguous_ids.add(cid)

    for cid in ambiguous_ids:
        conn.execute(
            "UPDATE identity_candidate_matches SET match_status = 'ambiguous' WHERE candidate_id = ?",
            (cid,),
        )
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

    print("Updating scores and confidence tiers...")
    update_scores_and_tiers(conn)
    print("Detecting collisions (ambiguous matches)...")
    detect_collisions(conn)

    for tier in ("A", "B", "C", "D"):
        n = conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE confidence_tier = ?", (tier,)).fetchone()[0]
        print(f"  Tier {tier}: {n}")
    amb = conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE match_status = 'ambiguous'").fetchone()[0]
    print(f"  Ambiguous: {amb}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
