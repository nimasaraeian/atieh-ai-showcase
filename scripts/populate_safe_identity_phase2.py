# -*- coding: utf-8 -*-
"""
Phase 2: Populate safe_identity_matches_phase2 from Tier A non-ambiguous candidates.
A2 -> primary_anchor; A3 and B1 -> labeled by source rule.
Does NOT update patients or payments.patient_id.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"
DOCS_REPORTS = REPO / "docs" / "reports"

# Only these rules are promoted (Tier A in practice)
PROMOTION_REASON_MAP = {
    "A2_phone_exact_name_exact": "primary_anchor",
    "A3_phone_exact_name_high_sim": "A3_phone_exact_name_high_sim",
    "B1_phone_exact_only": "B1_phone_exact_only",
}


def run_schema(conn) -> None:
    path = SQL_DIR / "003_safe_promotion_phase2.sql"
    if path.exists():
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def populate(conn) -> int:
    conn.execute("DELETE FROM safe_identity_matches_phase2")
    conn.commit()

    # Tier A, non-ambiguous only; only rules we consider safe
    rows = conn.execute("""
        SELECT left_source_type, left_row_id, right_source_type, right_row_id,
               candidate_rule, score_raw, confidence_tier, match_status
        FROM identity_candidate_matches
        WHERE confidence_tier = 'A'
          AND match_status != 'ambiguous'
          AND candidate_rule IN ('A2_phone_exact_name_exact', 'A3_phone_exact_name_high_sim', 'B1_phone_exact_only')
    """).fetchall()

    ins = """
        INSERT INTO safe_identity_matches_phase2 (
            left_source_type, left_row_id, right_source_type, right_row_id,
            candidate_rule, score_raw, confidence_tier, match_status, promotion_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for r in rows:
        left_type, left_id, right_type, right_id, rule, score, tier, status = r
        promotion_reason = PROMOTION_REASON_MAP.get(rule, rule)
        conn.execute(ins, (left_type, left_id, right_type, right_id, rule, score, tier, status, promotion_reason))
    conn.commit()
    return len(rows)


def _int(cursor) -> int:
    return cursor.fetchone()[0] if cursor else 0


def write_phase2_report(conn) -> None:
    DOCS_REPORTS.mkdir(parents=True, exist_ok=True)
    out = DOCS_REPORTS / "patient_identity_resolution_phase2_safe_promotion_report.md"

    total = _int(conn.execute("SELECT COUNT(*) FROM safe_identity_matches_phase2"))
    by_rule = conn.execute("""
        SELECT candidate_rule, promotion_reason, COUNT(*) AS cnt
        FROM safe_identity_matches_phase2
        GROUP BY candidate_rule, promotion_reason
        ORDER BY cnt DESC
    """).fetchall()
    by_pair = conn.execute("""
        SELECT left_source_type, right_source_type, COUNT(*) AS cnt
        FROM safe_identity_matches_phase2
        GROUP BY left_source_type, right_source_type
        ORDER BY cnt DESC
    """).fetchall()
    samples = conn.execute("""
        SELECT left_source_type, left_row_id, right_source_type, right_row_id,
               candidate_rule, score_raw, promotion_reason
        FROM safe_identity_matches_phase2
        ORDER BY promotion_reason, left_source_type, left_row_id
        LIMIT 15
    """).fetchall()

    lines = [
        "# Patient Identity Resolution Phase 2 – Safe Promotion Report",
        "",
        "## Summary",
        "",
        f"- **Total promoted safe matches:** {total}",
        "- **Criteria:** `confidence_tier = 'A'` and `match_status != 'ambiguous'`",
        "- **Rules promoted:** A2 (primary anchor), A3, B1 only",
        "",
        "## Promoted matches by rule",
        "",
        "| candidate_rule | promotion_reason | count |",
        "|----------------|------------------|-------|",
    ]
    for rule, reason, cnt in by_rule:
        lines.append(f"| {rule} | {reason} | {cnt} |")
    lines.extend([
        "",
        "## Promoted matches by pair type",
        "",
        "| left_source_type | right_source_type | count |",
        "|------------------|-------------------|-------|",
    ])
    for left, right, cnt in by_pair:
        lines.append(f"| {left} | {right} | {cnt} |")
    lines.extend([
        "",
        "## Sample rows",
        "",
        "| left_source_type | left_row_id | right_source_type | right_row_id | candidate_rule | score_raw | promotion_reason |",
        "|------------------|-------------|-------------------|--------------|----------------|-----------|------------------|",
    ])
    for r in samples:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} |")
    lines.extend([
        "",
        "## Why B2_name_exact_only is excluded from safe promotion",
        "",
        "B2 (name exact only) is **not** promoted to the safe table because:",
        "",
        "- **No phone evidence:** A match on normalized name alone can link many payment/appointment rows to many patients (e.g. common names, family members sharing a surname).",
        "- **High collision risk:** One name key can map to multiple patient_ids; promoting B2 would create ambiguous links.",
        "- **Policy:** Safe promotion requires at least **phone exact** (A2, A3, B1) so that the same phone anchors the identity. B2 has no phone signal.",
        "",
        "B2 remains in `identity_candidate_matches` for analysis and possible future fuzzy-review workflow, but is not written to `safe_identity_matches_phase2`.",
        "",
        "---",
        "",
        "*No updates were made to `patients` or `payments.patient_id`. This phase only populates the safe promotion table.*",
        "",
    ])
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


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
    n = populate(conn)
    print(f"Promoted {n} safe Tier A non-ambiguous matches into safe_identity_matches_phase2")
    write_phase2_report(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
