# -*- coding: utf-8 -*-
"""
Phase 4: Build identity_phase4_cluster_members, compute metrics, write report.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"
DOCS_REPORTS = REPO / "docs" / "reports"

ANCHOR_BASELINE = 27164
TARGET_80K = 80000


def run_schema(conn) -> None:
    for name in ("008_phase4_multihop_propagation_schema.sql", "009_phase4_multihop_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _int(cursor) -> int:
    return cursor.fetchone()[0] if cursor else 0


def build_cluster_members(conn) -> None:
    conn.execute("DELETE FROM identity_phase4_cluster_members")
    conn.commit()
    # Anchors
    for row in conn.execute("SELECT patient_id FROM identity_anchor_patients_phase3").fetchall():
        pid = row[0]
        conn.execute("""
            INSERT INTO identity_phase4_cluster_members (cluster_id, patient_id, source_origin, rule_used, confidence_level)
            VALUES (?, ?, 'anchor_phase2', 'phase2_safe', 'A')
        """, (pid, pid))
    # Phase3b promoted
    try:
        for row in conn.execute("""
            SELECT unrecovered_patient_id, anchor_patient_id, candidate_rule, confidence_level
            FROM patient_anchor_promoted_phase3b
        """).fetchall():
            ur_id, anchor_id, rule, conf = row
            conn.execute("""
                INSERT INTO identity_phase4_cluster_members (cluster_id, patient_id, source_origin, rule_used, confidence_level)
                VALUES (?, ?, 'phase3b_promoted', ?, ?)
            """, (anchor_id, ur_id, rule or "P3B", conf or "PROMOTE"))
    except Exception:
        pass
    # Phase4 promoted
    for row in conn.execute("""
        SELECT unrecovered_patient_id, cluster_id, propagation_rule, confidence_level
        FROM identity_phase4_promoted
    """).fetchall():
        ur_id, cluster_id, rule, conf = row
        conn.execute("""
            INSERT INTO identity_phase4_cluster_members (cluster_id, patient_id, source_origin, rule_used, confidence_level)
            VALUES (?, ?, 'phase4_promoted', ?, ?)
        """, (cluster_id, ur_id, rule or "P4", conf or "PROMOTE"))
    conn.commit()


def write_report(conn) -> None:
    out = DOCS_REPORTS / "patient_identity_resolution_phase4_report.md"

    total_patients = _int(conn.execute("SELECT COUNT(*) FROM patients"))
    phase4_new = _int(conn.execute("SELECT COUNT(DISTINCT unrecovered_patient_id) FROM identity_phase4_promoted"))
    phase3b_new = 0
    try:
        phase3b_new = _int(conn.execute("SELECT COUNT(DISTINCT unrecovered_patient_id) FROM patient_anchor_promoted_phase3b"))
    except Exception:
        pass
    total_recovered = _int(conn.execute("""
        SELECT COUNT(DISTINCT patient_id) FROM identity_phase4_cluster_members
    """))
    coverage_pct = round(total_recovered / total_patients * 100, 2) if total_patients else 0
    gap = TARGET_80K - total_recovered

    by_rule = conn.execute("""
        SELECT propagation_rule, COUNT(*) FROM identity_phase4_promoted GROUP BY propagation_rule ORDER BY 2 DESC
    """).fetchall()
    ambiguous = _int(conn.execute("SELECT COUNT(*) FROM identity_phase4_candidates WHERE match_status = 'ambiguous'"))
    total_cand = _int(conn.execute("SELECT COUNT(*) FROM identity_phase4_candidates"))
    promoted_count = _int(conn.execute("SELECT COUNT(*) FROM identity_phase4_promoted"))
    evidence_rows = _int(conn.execute("SELECT COUNT(*) FROM identity_cluster_evidence_phase4"))
    clusters_with_evidence = _int(conn.execute("SELECT COUNT(DISTINCT cluster_id) FROM identity_cluster_evidence_phase4"))

    lines = [
        "# Patient Identity Resolution Phase 4 – Multi-hop Propagation Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        "",
        f"- **Anchor patients (baseline):** {ANCHOR_BASELINE}",
        f"- **Newly recovered via phase3b:** {phase3b_new}",
        f"- **Newly recovered via phase4 propagation:** {phase4_new}",
        f"- **Total recovered patients (distinct in clusters):** {total_recovered}",
        f"- **Total patients in DB:** {total_patients}",
        f"- **Coverage %:** {coverage_pct}%",
        f"- **Gap to 80k:** {gap}",
        "",
        "## Cluster evidence",
        "",
        f"- **Evidence rows (phase2 + phase3 linked):** {evidence_rows}",
        f"- **Clusters with evidence:** {clusters_with_evidence}",
        "",
        "## Phase4 promotion by rule",
        "",
        "| propagation_rule | count |",
        "|------------------|-------|",
    ]
    for rule, cnt in by_rule:
        lines.append(f"| {rule} | {cnt} |")
    lines.extend([
        "",
        "## Ambiguity and safety",
        "",
        f"- **Total phase4 candidates:** {total_cand}",
        f"- **Promoted:** {promoted_count}",
        f"- **Ambiguous (not promoted):** {ambiguous}",
        "",
        "---",
        "",
        "*No updates to `patients` or `payments.patient_id`. Propagation uses payment/appointment linked evidence from phase2 and phase3; repeated shared phone across clusters is penalized; dominance margin 15.*",
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
    print("Built identity_phase4_cluster_members")
    write_report(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
