# -*- coding: utf-8 -*-
"""
Master Patient Profile V2 – read-only stats and report generation.

Payments-first identity model. Report includes:
- Distinct payment identity entities
- Distinct patients linked, patient coverage %
- Payment row coverage %
- Share of Tier A / Tier B deterministic links
- Review queue size (review_flag=1)
- Comparison to V1 (~20%) and recommendation
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent


def _int(cursor) -> int:
    return cursor.fetchone()[0] if cursor else 0


def _float(cursor) -> float:
    row = cursor.fetchone()
    return (row[0] or 0.0) if row else 0.0


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    import sqlite3
    conn = sqlite3.connect(db_path)

    # 1. Distinct payment identity entities
    distinct_identity_entities = _int(conn.execute("SELECT COUNT(*) FROM payment_identity_master"))

    # 2. Distinct patients linked (from v2 profile)
    distinct_patients_linked = _int(conn.execute("SELECT COUNT(DISTINCT patient_id) FROM master_patient_profile_v2"))
    total_patients = _int(conn.execute("SELECT COUNT(*) FROM patients_identity_normalized"))
    patient_coverage_pct = (distinct_patients_linked / total_patients * 100) if total_patients else 0.0

    # 3. Payment row coverage
    payment_rows_covered = _int(conn.execute("SELECT COALESCE(SUM(payment_rows_count), 0) FROM master_patient_profile_v2"))
    total_payment_rows_denom = _int(conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''"
    ))
    payment_row_coverage_pct = (payment_rows_covered / total_payment_rows_denom * 100) if total_payment_rows_denom else 0.0

    # 4. Tier A / B share (deterministic)
    tier_breakdown = conn.execute(
        "SELECT link_tier, COUNT(*) FROM master_patient_profile_v2 GROUP BY link_tier ORDER BY link_tier"
    ).fetchall()
    tier_counts = dict(tier_breakdown)
    tier_a = tier_counts.get("A", 0)
    tier_b = tier_counts.get("B", 0)
    tier_c = tier_counts.get("C", 0)
    tier_d = tier_counts.get("D", 0)
    v2_rows = _int(conn.execute("SELECT COUNT(*) FROM master_patient_profile_v2"))
    tier_a_pct = (tier_a / v2_rows * 100) if v2_rows else 0
    tier_b_pct = (tier_b / v2_rows * 100) if v2_rows else 0
    tier_ab_pct = ((tier_a + tier_b) / v2_rows * 100) if v2_rows else 0

    # 5. Review queue (review_flag=1)
    review_queue_size = _int(conn.execute("SELECT COUNT(*) FROM master_patient_profile_v2 WHERE review_flag = 1"))
    review_reason_breakdown = conn.execute(
        "SELECT review_reason, COUNT(*) FROM patient_master_link_v2 WHERE review_flag = 1 GROUP BY review_reason"
    ).fetchall()

    # 6. Identity strength breakdown
    strength_breakdown = conn.execute(
        "SELECT identity_strength_tier, COUNT(*) FROM master_patient_profile_v2 GROUP BY identity_strength_tier ORDER BY identity_strength_tier"
    ).fetchall()

    # 7. Unlinked payment identities (in master but no link)
    linked_codes = _int(conn.execute("SELECT COUNT(*) FROM patient_master_link_v2"))
    unlinked_identities = distinct_identity_entities - linked_codes

    conn.close()

    # Recommendation: does coverage move far beyond 20%? (V1 was ~20% payment coverage, ~27.6k patients)
    beyond_20 = payment_row_coverage_pct > 50 and distinct_patients_linked > 27000
    coverage_verdict = (
        "**Yes – coverage moves far beyond 20%.**" if beyond_20 else
        "**Coverage improved; monitor Tier A/B share and review queue.**" if payment_row_coverage_pct > 25 else
        "**Coverage still limited; consider additional signals or manual review.**"
    )

    # Build report
    report_path = REPO / "docs" / "reports" / "master_patient_profile_v2_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Master Patient Profile V2 Report",
        "",
        "Payments-first master identity architecture. Built from payment_identity_master, patient_master_link_v2, and patients_identity_normalized.",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## 1. Distinct payment identity entities",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| payment_identity_master (distinct financial identities) | {distinct_identity_entities:,} |",
        f"| Linked to a patient (patient_master_link_v2) | {linked_codes:,} |",
        f"| Unlinked (identity only, no patient) | {unlinked_identities:,} |",
        "",
        "## 2. Distinct patients linked & patient coverage %",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Distinct patient_id in master_patient_profile_v2 | {distinct_patients_linked:,} |",
        f"| Total patients (patients_identity_normalized) | {total_patients:,} |",
        f"| **Patient coverage %** | {patient_coverage_pct:.2f}% |",
        "",
        "## 3. Payment row coverage %",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Payment rows covered (sum of payment_rows_count in v2) | {payment_rows_covered:,} |",
        f"| Total payment rows with extracted code (denominator) | {total_payment_rows_denom:,} |",
        f"| **Payment row coverage %** | {payment_row_coverage_pct:.2f}% |",
        "",
        "## 4. Share of deterministic Tier A / Tier B links",
        "",
        f"| link_tier | Count | % of linked |",
        f"|-----------|-------|-------------|",
        f"| A | {tier_a:,} | {tier_a_pct:.1f}% |",
        f"| B | {tier_b:,} | {tier_b_pct:.1f}% |",
        f"| C | {tier_c:,} | {(tier_c / v2_rows * 100) if v2_rows else 0:.1f}% |",
        f"| D | {tier_d:,} | {(tier_d / v2_rows * 100) if v2_rows else 0:.1f}% |",
        f"| **A+B (deterministic)** | **{tier_a + tier_b:,}** | **{tier_ab_pct:.1f}%** |",
        "",
        "## 5. Review queue size",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Rows with review_flag=1 | {review_queue_size:,} |",
        f"| % of master_patient_profile_v2 | {(review_queue_size / v2_rows * 100) if v2_rows else 0:.1f}% |",
        "",
        "### Review reason breakdown",
        "",
        "| review_reason | Count |",
        "|---------------|-------|",
    ]
    for reason, cnt in review_reason_breakdown:
        lines.append(f"| {reason or '(null)'} | {cnt:,} |")
    lines.extend([
        "",
        "## 6. Identity strength (payment side)",
        "",
        "| identity_strength_tier | Count |",
        "|------------------------|-------|",
    ])
    for tier, cnt in strength_breakdown:
        lines.append(f"| {tier or '(null)'} | {cnt:,} |")
    lines.extend([
        "",
        "## 7. Does coverage move far beyond 20%?",
        "",
        coverage_verdict,
        "",
        "---",
        "",
        "## Run order (from repo root)",
        "",
        "1. Schema: `sqlite3 atieh_clinic_recovery81_test.db < sql/identity_resolution/014_payment_identity_master_v2_schema.sql`",
        "2. Payment identity master: `python scripts/build_payment_identity_master_v2.py`",
        "3. Patient links: `python scripts/build_patient_master_link_v2.py`",
        "4. Profile v2: `python scripts/build_master_patient_profile_v2.py`",
        "5. This report: `python scripts/master_patient_profile_v2_stats.py`",
        "",
        "## Sample query patterns for backend/API",
        "",
        "Search by CRM code: `SELECT * FROM master_patient_profile_v2 WHERE crm_patient_code = ?`",
        "",
        "Search by patient name_key: `SELECT * FROM master_patient_profile_v2 WHERE patient_name_key = ?`",
        "",
        "Search by phone: `SELECT * FROM master_patient_profile_v2 WHERE primary_phone = ?`",
        "",
        "Fetch by patient_id: `SELECT * FROM master_patient_profile_v2 WHERE patient_id = ?`",
        "",
        "Only high-confidence (no review): `SELECT * FROM master_patient_profile_v2 WHERE review_flag = 0`",
        "",
        "## Validation queries (SQLite)",
        "",
        "```sql",
        "SELECT COUNT(*) AS payment_identity_entities FROM payment_identity_master;",
        "SELECT COUNT(DISTINCT patient_id) AS distinct_patients FROM master_patient_profile_v2;",
        "SELECT SUM(payment_rows_count) AS payment_rows_covered FROM master_patient_profile_v2;",
        "SELECT link_tier, COUNT(*) FROM master_patient_profile_v2 GROUP BY link_tier;",
        "SELECT COUNT(*) AS review_count FROM patient_master_link_v2 WHERE review_flag = 1;",
        "```",
        "",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {report_path}")
    print(f"  Payment identities: {distinct_identity_entities:,}  |  Patients linked: {distinct_patients_linked:,}  |  Patient coverage: {patient_coverage_pct:.1f}%")
    print(f"  Payment row coverage: {payment_row_coverage_pct:.1f}%  |  Tier A+B: {tier_ab_pct:.1f}%  |  Review queue: {review_queue_size:,}")


if __name__ == "__main__":
    main()
