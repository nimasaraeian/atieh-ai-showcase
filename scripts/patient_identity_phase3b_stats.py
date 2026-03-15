# -*- coding: utf-8 -*-
"""
Phase 3B: Build patient_cluster_members_phase3b, compute metrics, write report.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"
DOCS_REPORTS = REPO / "docs" / "reports"

ANCHOR_COUNT_BASELINE = 27164
TARGET_ASPIRATION = 80000


def run_schema(conn) -> None:
    for name in (
        "006_phase3b_anchored_patient_expansion_schema.sql",
        "007_phase3b_anchored_patient_expansion_indexes.sql",
    ):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _int(cursor) -> int:
    return cursor.fetchone()[0] if cursor else 0


def build_cluster_members(conn) -> None:
    conn.execute("DELETE FROM patient_cluster_members_phase3b")
    conn.commit()
    # Anchors: cluster_id = patient_id, patient_id = same, source_origin = anchor_phase2
    for row in conn.execute("SELECT patient_id FROM identity_anchor_patients_phase3").fetchall():
        pid = row[0]
        conn.execute("""
            INSERT INTO patient_cluster_members_phase3b (cluster_id, patient_id, source_origin, rule_used, confidence_level)
            VALUES (?, ?, 'anchor_phase2', 'phase2_safe', 'A')
        """, (pid, pid))
    # Promoted unrecovered: cluster_id = anchor_patient_id, patient_id = unrecovered_patient_id
    for row in conn.execute("""
        SELECT unrecovered_patient_id, anchor_patient_id, candidate_rule, confidence_level
        FROM patient_anchor_promoted_phase3b
    """).fetchall():
        ur_id, anchor_id, rule, conf = row
        conn.execute("""
            INSERT INTO patient_cluster_members_phase3b (cluster_id, patient_id, source_origin, rule_used, confidence_level)
            VALUES (?, ?, 'phase3b_promoted', ?, ?)
        """, (anchor_id, ur_id, rule or "P3B", conf or "PROMOTE"))
    conn.commit()


def write_report(conn) -> None:
    out = DOCS_REPORTS / "patient_identity_resolution_phase3b_report.md"

    total_patients = _int(conn.execute("SELECT COUNT(*) FROM patients"))
    unrecovered_count = _int(conn.execute("SELECT COUNT(*) FROM unrecovered_patients_phase3b"))
    newly_recovered = _int(conn.execute("SELECT COUNT(DISTINCT unrecovered_patient_id) FROM patient_anchor_promoted_phase3b"))
    total_recovered = ANCHOR_COUNT_BASELINE + newly_recovered
    coverage_pct = round(total_recovered / total_patients * 100, 2) if total_patients else 0

    by_rule = conn.execute("""
        SELECT candidate_rule, COUNT(*) FROM patient_anchor_promoted_phase3b GROUP BY candidate_rule ORDER BY 2 DESC
    """).fetchall()
    ambiguous_count = _int(conn.execute("SELECT COUNT(*) FROM patient_anchor_candidates_phase3b WHERE match_status = 'ambiguous'"))
    reject_count = _int(conn.execute("SELECT COUNT(*) FROM patient_anchor_candidates_phase3b WHERE confidence_level = 'REJECT'"))
    review_count = _int(conn.execute("SELECT COUNT(*) FROM patient_anchor_candidates_phase3b WHERE confidence_level = 'REVIEW'"))
    total_candidates = _int(conn.execute("SELECT COUNT(*) FROM patient_anchor_candidates_phase3b"))
    promoted_count = _int(conn.execute("SELECT COUNT(*) FROM patient_anchor_promoted_phase3b"))

    gap_to_80k = TARGET_ASPIRATION - total_recovered

    lines = [
        "# Patient Identity Resolution Phase 3B – Anchored Patient Expansion Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "**Scoring (patient recovery):** record_no +90, phone +70, exact name +35, high name sim +20, repeated cluster phone +25, repeated cluster record_no +35. Name-only rejected; phone-only REVIEW; promote: phone+exact name, record_no (+ support or unique), repeated cluster phone+name, repeated cluster record_no+name. Dominance margin 15.",
        "",
        "## Summary",
        "",
        f"- **Anchor patients (baseline):** {ANCHOR_COUNT_BASELINE}",
        f"- **Unrecovered patients (candidates for expansion):** {unrecovered_count}",
        f"- **Newly recovered patients (promoted to anchor cluster):** {newly_recovered}",
        f"- **Total recovered patients:** {total_recovered}",
        f"- **Total patients in DB:** {total_patients}",
        f"- **Coverage %:** {coverage_pct}%",
        "",
        "## Promotion by rule",
        "",
        "| candidate_rule | count |",
        "|----------------|-------|",
    ]
    for rule, cnt in by_rule:
        lines.append(f"| {rule} | {cnt} |")
    lines.extend([
        "",
        "## Ambiguity and safety",
        "",
        f"- **Total candidates:** {total_candidates}",
        f"- **Promoted:** {promoted_count}",
        f"- **Ambiguous (not promoted):** {ambiguous_count}",
        f"- **REVIEW (not promoted):** {review_count}",
        f"- **REJECT:** {reject_count}",
        "",
        "## Path toward 80k",
        "",
        f"- **Gap to 80,000 target:** {gap_to_80k}",
        "",
        "Phase 3B recovers additional patients by linking unrecovered patient records to anchor patients via phone, record_no, and name evidence. To approach 80k:",
        "- Continue strengthening record_no and phone coverage in source data.",
        "- Consider manual review queue for REVIEW-level candidates.",
        "- Optional: iterative expansion (e.g. treat promoted unrecovered as secondary anchors for further linking).",
        "- No global name-only promotion; safety rules are unchanged.",
        "",
        "---",
        "",
        "*No updates were made to `patients` or `payments.patient_id`.*",
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

    DOCS_REPORTS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA busy_timeout = 30000")
    run_schema(conn)
    build_cluster_members(conn)
    print("Built patient_cluster_members_phase3b")
    write_report(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
