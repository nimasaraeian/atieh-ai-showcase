# -*- coding: utf-8 -*-
"""
Phase 3: Build identity_cluster_members_phase3, compute metrics, write reports.
Includes payment↔appointment phone-overlap diagnostic.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"
DOCS_REPORTS = REPO / "docs" / "reports"

BASELINE_ANCHOR_PATIENTS = 27164
TARGET_ASPIRATION = 80000


def run_schema(conn) -> None:
    for name in ("004_phase3_graph_expansion_schema.sql", "005_phase3_graph_expansion_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _int(cursor) -> int:
    return cursor.fetchone()[0] if cursor else 0


def build_cluster_members(conn) -> None:
    conn.execute("DELETE FROM identity_cluster_members_phase3")
    conn.commit()
    # Phase2 safe: cluster_id = patient_id (right_row_id), source = left
    for row in conn.execute("""
        SELECT right_row_id, left_source_type, left_row_id, candidate_rule
        FROM safe_identity_matches_phase2
        WHERE right_source_type = 'patient'
    """).fetchall():
        patient_id, src_type, src_id, rule = row
        conn.execute("""
            INSERT INTO identity_cluster_members_phase3 (cluster_id, patient_id, source_type, source_row_id, source_origin, rule_used, confidence_level)
            VALUES (?, ?, ?, ?, 'phase2_safe', ?, 'A')
        """, (patient_id, patient_id, src_type, src_id, rule))
    # Phase3 promoted
    for row in conn.execute("""
        SELECT target_patient_id, source_type, source_row_id, expansion_rule, confidence_level
        FROM identity_expansion_promoted_phase3
    """).fetchall():
        patient_id, src_type, src_id, rule, conf = row
        conn.execute("""
            INSERT INTO identity_cluster_members_phase3 (cluster_id, patient_id, source_type, source_row_id, source_origin, rule_used, confidence_level)
            VALUES (?, ?, ?, ?, 'phase3_expanded', ?, ?)
        """, (patient_id, patient_id, src_type, src_id, rule, conf or ""))
    conn.commit()


def payment_appointment_phone_diagnostic(conn) -> dict:
    """Compare phone normalization overlap between payments and appointments."""
    pay_phones = set(
        row[0] for row in conn.execute("""
            SELECT DISTINCT mobile_primary_norm FROM identity_normalized_payments
            WHERE mobile_primary_norm IS NOT NULL AND TRIM(mobile_primary_norm) <> ''
        """).fetchall()
    )
    app_phones = set(
        row[0] for row in conn.execute("""
            SELECT DISTINCT phone_primary_norm FROM identity_normalized_appointments
            WHERE phone_primary_norm IS NOT NULL AND TRIM(phone_primary_norm) <> ''
        """).fetchall()
    )
    overlap = pay_phones & app_phones
    return {
        "distinct_payment_phones": len(pay_phones),
        "distinct_appointment_phones": len(app_phones),
        "overlapping_phones": len(overlap),
    }


def write_graph_expansion_report(conn) -> None:
    out = DOCS_REPORTS / "patient_identity_resolution_phase3_graph_expansion_report.md"

    # K1 Anchor metrics
    total_anchors = _int(conn.execute("SELECT COUNT(*) FROM identity_anchor_patients_phase3"))
    primary_anchors = _int(conn.execute("SELECT COUNT(*) FROM identity_anchor_patients_phase3 WHERE primary_anchor_count > 0"))
    avg_links = conn.execute("SELECT AVG(anchor_match_count) FROM identity_anchor_patients_phase3").fetchone()[0] or 0

    # K2 Anchor evidence
    distinct_phones = _int(conn.execute("SELECT COUNT(DISTINCT phone_norm) FROM identity_anchor_phone_phase3"))
    distinct_recordnos = _int(conn.execute("SELECT COUNT(DISTINCT record_no_norm) FROM identity_anchor_recordno_phase3"))
    distinct_names = _int(conn.execute("SELECT COUNT(DISTINCT patient_name_key) FROM identity_anchor_name_phase3"))
    anchors_multi_phone = _int(conn.execute("""
        SELECT COUNT(*) FROM (SELECT patient_id FROM identity_anchor_phone_phase3 GROUP BY patient_id HAVING COUNT(*) > 1)
    """))
    anchors_multi_recordno = _int(conn.execute("""
        SELECT COUNT(*) FROM (SELECT patient_id FROM identity_anchor_recordno_phase3 GROUP BY patient_id HAVING COUNT(*) > 1)
    """))

    # K3 Expansion candidates
    total_candidates = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_candidates_phase3"))
    cand_by_source = conn.execute("""
        SELECT source_type, COUNT(*) FROM identity_expansion_candidates_phase3 GROUP BY source_type
    """).fetchall()
    cand_by_rule = conn.execute("""
        SELECT expansion_rule, COUNT(*) FROM identity_expansion_candidates_phase3 WHERE expansion_rule IS NOT NULL GROUP BY expansion_rule ORDER BY 2 DESC
    """).fetchall()
    cand_by_support = conn.execute("""
        SELECT support_signal_count, COUNT(*) FROM identity_expansion_candidates_phase3 GROUP BY support_signal_count ORDER BY 1
    """).fetchall()
    ambiguous_count = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_candidates_phase3 WHERE match_status = 'ambiguous'"))

    # K4 Promotion
    total_promoted = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_promoted_phase3"))
    prom_by_rule = conn.execute("""
        SELECT expansion_rule, COUNT(*) FROM identity_expansion_promoted_phase3 GROUP BY expansion_rule ORDER BY 2 DESC
    """).fetchall()
    prom_by_conf = conn.execute("""
        SELECT confidence_level, COUNT(*) FROM identity_expansion_promoted_phase3 GROUP BY confidence_level
    """).fetchall()
    prom_payment = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_promoted_phase3 WHERE source_type = 'payment'"))
    prom_appointment = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_promoted_phase3 WHERE source_type = 'appointment'"))

    # K5 Coverage
    unique_after = _int(conn.execute("""
        SELECT COUNT(DISTINCT patient_id) FROM (
            SELECT right_row_id AS patient_id FROM safe_identity_matches_phase2 WHERE right_source_type = 'patient'
            UNION
            SELECT target_patient_id AS patient_id FROM identity_expansion_promoted_phase3
        )
    """))
    increase = unique_after - BASELINE_ANCHOR_PATIENTS
    pct = (increase / BASELINE_ANCHOR_PATIENTS * 100) if BASELINE_ANCHOR_PATIENTS else 0
    gap_to_target = TARGET_ASPIRATION - unique_after

    # K6 Safety
    rejected_amb = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_candidates_phase3 WHERE match_status = 'ambiguous'"))
    by_rule_amb = conn.execute("""
        SELECT expansion_rule, COUNT(*) FROM identity_expansion_candidates_phase3 WHERE match_status = 'ambiguous' GROUP BY expansion_rule ORDER BY 2 DESC LIMIT 10
    """).fetchall()
    review_count = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_candidates_phase3 WHERE confidence_level = 'REVIEW'"))
    reject_count = _int(conn.execute("SELECT COUNT(*) FROM identity_expansion_candidates_phase3 WHERE confidence_level = 'REJECT'"))

    # K7 Record_no
    prom_recordno_rules = conn.execute("""
        SELECT expansion_rule, COUNT(*) FROM identity_expansion_promoted_phase3
        WHERE expansion_rule LIKE 'P1%' OR expansion_rule LIKE 'P3%'
        GROUP BY expansion_rule
    """).fetchall()
    recordno_promotions = sum(c for _, c in prom_recordno_rules)
    sample_promoted = conn.execute("""
        SELECT source_type, source_row_id, target_patient_id, expansion_rule, support_signal_count, score_raw, confidence_level
        FROM identity_expansion_promoted_phase3 ORDER BY promoted_id LIMIT 10
    """).fetchall()

    lines = [
        "# Patient Identity Resolution Phase 3 – Graph Expansion Report",
        "",
        "**Scoring weights (documented):** record_no +80, phone +60, exact name +40, high name sim +25, repeated cluster phone/recordno +20 each, same year +10, date compatible +10. Penalties: one weak signal -50, phone match name conflict -35. Dominance margin: 15.",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## K1) Anchor metrics",
        "",
        f"- **Total anchor patients:** {total_anchors}",
        f"- **Anchor patients with primary_anchor (A2):** {primary_anchors}",
        f"- **Average safe links per anchor patient:** {round(avg_links, 2)}",
        "",
        "## K2) Anchor evidence metrics",
        "",
        f"- **Total distinct phones across anchors:** {distinct_phones}",
        f"- **Total distinct record_nos:** {distinct_recordnos}",
        f"- **Total distinct names:** {distinct_names}",
        f"- **Anchors with multiple phones:** {anchors_multi_phone}",
        f"- **Anchors with multiple record_nos:** {anchors_multi_recordno}",
        "",
        "## K3) Expansion candidate metrics",
        "",
        f"- **Total candidates generated:** {total_candidates}",
        "- **By source_type:**",
    ]
    for src, cnt in cand_by_source:
        lines.append(f"  - {src}: {cnt}")
    lines.append("- **By rule:**")
    for rule, cnt in cand_by_rule:
        lines.append(f"  - {rule}: {cnt}")
    lines.append("- **By support_signal_count:**")
    for sup, cnt in cand_by_support:
        lines.append(f"  - {sup}: {cnt}")
    lines.append(f"- **Ambiguous candidates:** {ambiguous_count}")
    lines.extend([
        "",
        "## K4) Promotion metrics",
        "",
        f"- **Total promoted phase3 matches:** {total_promoted}",
        "- **Promoted by rule:**",
    ])
    for rule, cnt in prom_by_rule:
        lines.append(f"  - {rule}: {cnt}")
    lines.append("- **By confidence level:**")
    for conf, cnt in prom_by_conf:
        lines.append(f"  - {conf}: {cnt}")
    lines.append(f"- **Promoted payment count:** {prom_payment}")
    lines.append(f"- **Promoted appointment count:** {prom_appointment}")
    lines.extend([
        "",
        "## K5) Coverage metrics",
        "",
        f"- **Baseline unique recovered patients (before phase3):** {BASELINE_ANCHOR_PATIENTS}",
        f"- **Unique recovered patients after phase3:** {unique_after}",
        f"- **Increase:** {increase}",
        "",
        "*(Phase3 links more payment/appointment rows to existing anchor patients; distinct patient count may stay at baseline. To approach 80000 would require additional anchor sources.)*",
        "",
        f"- **Increase percentage:** {round(pct, 2)}%",
        f"- **Gap to 80000 target:** {gap_to_target}",
        "",
        "## K6) Safety metrics",
        "",
        f"- **Rejected ambiguous candidates:** {rejected_amb}",
        "- **Top rules causing ambiguity:**",
    ])
    for rule, cnt in by_rule_amb:
        lines.append(f"  - {rule}: {cnt}")
    lines.append(f"- **REVIEW (not promoted):** {review_count}")
    lines.append(f"- **REJECT:** {reject_count}")
    lines.extend([
        "",
        "## K7) Record_no diagnostics",
        "",
        f"- **Promotions from record_no-supported rules (P1, P3):** {recordno_promotions}",
    ])
    for rule, cnt in prom_recordno_rules:
        lines.append(f"  - {rule}: {cnt}")
    lines.extend([
        "",
        "## Sample promoted rows (phase3)",
        "",
        "| source_type | source_row_id | target_patient_id | expansion_rule | support_signal_count | score_raw | confidence_level |",
        "|-------------|---------------|-------------------|----------------|----------------------|-----------|------------------|",
    ])
    for r in sample_promoted:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} |")
    lines.extend([
        "",
        "---",
        "",
        "## L) Reporting questions answered",
        "",
        f"1. **Unique patient anchors we started with:** {BASELINE_ANCHOR_PATIENTS}",
        f"2. **Unique patients covered after phase3:** {unique_after}",
        f"3. **Additional patients recovered:** {increase} (phase3 adds links to existing anchors; new distinct patients only if expansion linked previously unlinked records to anchors).",
        "4. **Which expansion rule contributed the most:** See promoted by rule above.",
        "5. **Did record_no materially improve coverage:** See K7; record_no-supported rules (P1, P3) contributed as above.",
        "6. **Is phone still the main bridge:** Yes for phase2 anchors; phase3 expansion uses phone + record_no + name in combination.",
        f"7. **Candidates remaining ambiguous:** {ambiguous_count}",
        f"8. **How close to 80000:** {unique_after} recovered; gap {gap_to_target}. 80000 is an aspiration; actual coverage depends on data and safe rules.",
        "9. **Recommended next phase:** Choose among: final assignment layer (write to staging only); iterative graph expansion phase 4; record_no strengthening; manual review queue for REVIEW; payment↔appointment bridge repair.",
        "",
    ])
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


def write_rule_diagnostics(conn) -> None:
    out = DOCS_REPORTS / "patient_identity_resolution_phase3_rule_diagnostics.md"
    diag = payment_appointment_phone_diagnostic(conn)
    lines = [
        "# Phase 3 Rule Diagnostics",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Payment ↔ Appointment phone overlap (zero-candidate follow-up)",
        "",
        "Diagnostic counts:",
        f"- **Distinct payment phones (mobile_primary_norm):** {diag['distinct_payment_phones']}",
        f"- **Distinct appointment phones (phone_primary_norm):** {diag['distinct_appointment_phones']}",
        f"- **Overlapping distinct phones:** {diag['overlapping_phones']}",
        "",
        "**Interpretation:** If overlapping_phones is 0 or very low, payment↔appointment B7 candidates will be zero. Likely causes: normalization mismatch, different source coverage (e.g. appointment files missing or different years), or real data sparsity. If both counts are high but overlap is low, investigate column mapping and normalization consistency.",
        "",
    ]
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
    print("Built identity_cluster_members_phase3")
    write_graph_expansion_report(conn)
    write_rule_diagnostics(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
