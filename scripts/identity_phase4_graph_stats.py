# -*- coding: utf-8 -*-
"""
Phase 4: Build phase4_patient_recovered, write graph propagation report.
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
TARGET_100K = 100000


def run_schema(conn) -> None:
    for name in ("010_phase4_graph_propagation_schema.sql", "011_phase4_graph_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _int(cursor) -> int:
    return cursor.fetchone()[0] if cursor else 0


def build_patient_recovered(conn) -> None:
    conn.execute("DELETE FROM phase4_patient_recovered")
    conn.commit()
    # Anchors
    for r in conn.execute("SELECT patient_id FROM identity_anchor_patients_phase3").fetchall():
        conn.execute("""
            INSERT INTO phase4_patient_recovered (patient_id, cluster_id, recovery_source, propagation_rule, confidence_level)
            VALUES (?, ?, 'anchor_phase2', 'phase2_safe', 'A')
        """, (r[0], r[0]))
    # Phase3b promoted
    try:
        for r in conn.execute("SELECT unrecovered_patient_id, anchor_patient_id, candidate_rule, confidence_level FROM patient_anchor_promoted_phase3b").fetchall():
            conn.execute("""
                INSERT OR IGNORE INTO phase4_patient_recovered (patient_id, cluster_id, recovery_source, propagation_rule, confidence_level)
                VALUES (?, ?, 'phase3b_promoted', ?, ?)
            """, (r[0], r[1], r[2] or "P3B", r[3] or "PROMOTE"))
    except Exception:
        pass
    # Phase4 promoted
    for r in conn.execute("SELECT unrecovered_patient_id, cluster_id, propagation_rule, confidence_level FROM phase4_cluster_promoted").fetchall():
        conn.execute("""
            INSERT OR IGNORE INTO phase4_patient_recovered (patient_id, cluster_id, recovery_source, propagation_rule, confidence_level)
            VALUES (?, ?, 'phase4_promoted', ?, ?)
        """, (r[0], r[1], r[2] or "P4", r[3] or "PROMOTE"))
    conn.commit()


def write_report(conn) -> None:
    out = DOCS_REPORTS / "patient_identity_resolution_phase4_graph_propagation_report.md"

    total_patients = _int(conn.execute("SELECT COUNT(*) FROM patients"))
    total_recovered = _int(conn.execute("SELECT COUNT(DISTINCT patient_id) FROM phase4_patient_recovered"))
    phase4_new = _int(conn.execute("""
        SELECT COUNT(DISTINCT patient_id) FROM phase4_patient_recovered WHERE recovery_source = 'phase4_promoted'
    """))
    phase3b_new = 0
    try:
        phase3b_new = _int(conn.execute("""
            SELECT COUNT(DISTINCT patient_id) FROM phase4_patient_recovered WHERE recovery_source = 'phase3b_promoted'
        """))
    except Exception:
        pass
    coverage_pct = round(total_recovered / total_patients * 100, 2) if total_patients else 0
    gap_100k = TARGET_100K - total_recovered

    by_rule = conn.execute("""
        SELECT propagation_rule, COUNT(*) FROM phase4_cluster_promoted GROUP BY propagation_rule ORDER BY 2 DESC
    """).fetchall()
    ambiguous_count = _int(conn.execute("SELECT COUNT(*) FROM phase4_ambiguity_review"))
    primary_rule_count = _int(conn.execute("""
        SELECT COUNT(*) FROM phase4_cluster_promoted WHERE propagation_rule LIKE '%phone_primary%'
    """))
    all_phone_rule_count = _int(conn.execute("""
        SELECT COUNT(*) FROM phase4_cluster_promoted WHERE propagation_rule LIKE '%phone_all%' AND propagation_rule NOT LIKE '%phone_primary%'
    """))
    multi_hop_count = _int(conn.execute("""
        SELECT COUNT(*) FROM phase4_cluster_promoted WHERE propagation_rule LIKE '%_name%' OR propagation_rule LIKE '%_repeated%'
    """))

    lines = [
        "# Patient Identity Resolution Phase 4 – Graph Propagation Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        "",
        f"- **Total patients in DB:** {total_patients}",
        f"- **Anchor patients (baseline):** {ANCHOR_BASELINE}",
        f"- **Newly recovered via phase3b:** {phase3b_new}",
        f"- **Newly recovered via phase4 propagation:** {phase4_new}",
        f"- **Total recovered patients:** {total_recovered}",
        f"- **Coverage %:** {coverage_pct}%",
        f"- **Gap to 100k target:** {gap_100k}",
        "",
        "## Promotion by rule",
        "",
        "| propagation_rule | count |",
        "|------------------|-------|",
    ]
    for rule, cnt in by_rule:
        lines.append(f"| {rule} | {cnt} |")
    lines.extend([
        "",
        "## Growth by signal type",
        "",
        f"- **Promotions from primary-phone match:** {primary_rule_count}",
        f"- **Promotions from phone_all (expansion) only:** {all_phone_rule_count}",
        f"- **Promotions with name or repeated (multi-hop support):** {multi_hop_count}",
        "",
        "## Ambiguity",
        "",
        f"- **Ambiguous (competing targets, margin < 15):** {ambiguous_count}",
        "",
        "## Realistic upper bound toward 100k",
        "",
        f"Current recovered: {total_recovered}. Upper bound depends on: (1) share of unrecovered patients that share phone/name with anchor clusters; (2) avoiding false merges (dominance + no global name-only). Phase4 uses graph propagation (phase4_phone_patient_links, phase4_name_patient_links) from phase2+phase3 linked evidence. To approach 100k would require additional anchor coverage or manual review of ambiguity_review and REVIEW-level candidates.",
        "",
        "---",
        "",
        "*No updates to `patients` or `payments.patient_id`.*",
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
    build_patient_recovered(conn)
    print("Built phase4_patient_recovered")
    write_report(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
