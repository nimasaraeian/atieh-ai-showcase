# -*- coding: utf-8 -*-
"""
Master Patient Profile V1 – read-only stats and report generation.

Writes docs/reports/master_patient_profile_v1_report.md with:
- Total rows in v1 and review_queue
- Distinct patient_id / crm_patient_code in v1
- Payment coverage (rows and % of payments_crm_code_all_years)
- Breakdown by link_confidence and link_rule
- Risky/common-name and ambiguous exclusion counts
- Recommendation (safe for reception / safe with warnings / not safe enough)
- Sample query patterns for backend/API
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

    # --- Counts ---
    v1_rows = _int(conn.execute("SELECT COUNT(*) FROM master_patient_profile_v1"))
    review_rows = _int(conn.execute("SELECT COUNT(*) FROM master_patient_profile_review_queue"))
    distinct_patient_id_v1 = _int(conn.execute("SELECT COUNT(DISTINCT patient_id) FROM master_patient_profile_v1"))
    distinct_crm_code_v1 = _int(conn.execute("SELECT COUNT(DISTINCT crm_patient_code) FROM master_patient_profile_v1"))
    total_payment_rows_covered_v1 = _int(conn.execute("SELECT COALESCE(SUM(payment_rows_count), 0) FROM master_patient_profile_v1"))
    total_payments_denom = _int(conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''"
    ))
    pct_covered = (total_payment_rows_covered_v1 / total_payments_denom * 100) if total_payments_denom else 0.0

    # Breakdown by link_confidence
    confidence_breakdown = conn.execute(
        "SELECT link_confidence, COUNT(*) FROM master_patient_profile_v1 GROUP BY link_confidence ORDER BY link_confidence"
    ).fetchall()
    # Breakdown by link_rule
    rule_breakdown = conn.execute(
        "SELECT link_rule, COUNT(*) FROM master_patient_profile_v1 GROUP BY link_rule ORDER BY link_rule"
    ).fetchall()

    # Review queue: risky/common-name exclusions vs ambiguous
    review_common_name = _int(conn.execute(
        "SELECT COUNT(*) FROM master_patient_profile_review_queue WHERE ambiguity_reason = 'common_name_key'"
    ))
    review_was_ambiguous = _int(conn.execute(
        "SELECT COUNT(*) FROM master_patient_profile_review_queue WHERE ambiguity_reason = 'was_ambiguous'"
    ))
    review_no_financial = _int(conn.execute(
        "SELECT COUNT(*) FROM master_patient_profile_review_queue WHERE ambiguity_reason = 'no_financial_aggregate'"
    ))
    review_multiple_patients = _int(conn.execute(
        "SELECT COUNT(*) FROM master_patient_profile_review_queue WHERE ambiguity_reason = 'multiple_patients_per_code'"
    ))
    review_multiple_codes = _int(conn.execute(
        "SELECT COUNT(*) FROM master_patient_profile_review_queue WHERE ambiguity_reason = 'multiple_codes_per_patient'"
    ))

    conn.close()

    # --- Recommendation ---
    if v1_rows == 0:
        recommendation = "**Not safe enough** – no rows in V1; do not use for reception panel until links are re-evaluated."
    elif distinct_crm_code_v1 < 10000 and pct_covered < 50:
        recommendation = "**Safe only with warning badges** – low coverage; show a clear notice that many payments are not yet linked to a patient profile."
    elif review_common_name + review_was_ambiguous > v1_rows:
        recommendation = "**Safe only with warning badges** – many exclusions for ambiguity/common names; use V1 for search but flag unlinked payments."
    else:
        recommendation = "**Safe for reception panel** – use master_patient_profile_v1 for search by name, phone, CRM code; use review_queue for manual resolution of uncertain cases."

    # --- Build report ---
    report_path = REPO / "docs" / "reports" / "master_patient_profile_v1_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Master Patient Profile V1 Report",
        "",
        "Final safe, product-ready derived layer for reception/backend integration.",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## 1. Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total rows in **master_patient_profile_v1** | {v1_rows:,} |",
        f"| Total rows in **master_patient_profile_review_queue** | {review_rows:,} |",
        f"| Distinct **patient_id** in V1 | {distinct_patient_id_v1:,} |",
        f"| Distinct **crm_patient_code** in V1 | {distinct_crm_code_v1:,} |",
        f"| Total **payment_rows_count** covered by V1 | {total_payment_rows_covered_v1:,} |",
        f"| Total payment rows (payments_crm_code_all_years, with code) | {total_payments_denom:,} |",
        f"| **Percentage of payments covered by V1** | {pct_covered:.2f}% |",
        "",
        "## 2. Breakdown by link_confidence (V1)",
        "",
        "| link_confidence | Count |",
        "|------------------|-------|",
    ]
    for tier, cnt in confidence_breakdown:
        lines.append(f"| {tier or '(null)'} | {cnt:,} |")
    lines.extend([
        "",
        "## 3. Breakdown by link_rule (V1)",
        "",
        "| link_rule | Count |",
        "|-----------|-------|",
    ])
    for rule, cnt in rule_breakdown:
        lines.append(f"| {rule or '(null)'} | {cnt:,} |")
    lines.extend([
        "",
        "## 4. Exclusions (review_queue)",
        "",
        "| Reason | Count |",
        "|--------|-------|",
        f"| common_name_key (risky name_key duplication) | {review_common_name:,} |",
        f"| was_ambiguous (code had ambiguity history) | {review_was_ambiguous:,} |",
        f"| no_financial_aggregate | {review_no_financial:,} |",
        f"| multiple_patients_per_code | {review_multiple_patients:,} |",
        f"| multiple_codes_per_patient | {review_multiple_codes:,} |",
        "",
        "## 5. Recommendation",
        "",
        recommendation,
        "",
        "---",
        "",
        "## Sample query patterns for backend/API",
        "",
        "### Search by patient name (canonical or name_key)",
        "```sql",
        "SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, primary_phone, payment_rows_count, total_net_received",
        "FROM master_patient_profile_v1",
        "WHERE patient_name_key = :name_key",
        "   OR patient_name_canonical LIKE '%' || :query || '%';",
        "```",
        "",
        "### Search by phone",
        "```sql",
        "SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, primary_phone, payment_rows_count",
        "FROM master_patient_profile_v1",
        "WHERE primary_phone = :phone_norm;",
        "-- Or search inside all_phones_json if needed (JSON array).",
        "```",
        "",
        "### Search by CRM code",
        "```sql",
        "SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, primary_phone,",
        "       payment_rows_count, total_net_received, first_year, last_year, link_confidence, link_rule",
        "FROM master_patient_profile_v1",
        "WHERE crm_patient_code = :crm_code;",
        "```",
        "",
        "### Fetch full patient profile by patient_id",
        "```sql",
        "SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, patient_name_key,",
        "       primary_phone, all_phones_json, national_id_norm,",
        "       payment_rows_count, total_net_received, positive_net_received_sum, negative_net_received_sum,",
        "       first_year, last_year, link_confidence, link_rule, ambiguity_flag, ambiguity_reason",
        "FROM master_patient_profile_v1",
        "WHERE patient_id = :patient_id;",
        "```",
        "",
        "---",
        "",
        "## Run order (from repo root)",
        "",
        "1. Apply schema: `sqlite3 atieh_clinic_recovery81_test.db < sql/identity_resolution/013_master_patient_profile_v1_schema.sql`",
        "2. Build V1: `python scripts/build_master_patient_profile_v1.py`",
        "3. Generate this report: `python scripts/master_patient_profile_v1_stats.py`",
        "",
        "## Validate final counts (SQLite)",
        "",
        "```sql",
        "SELECT COUNT(*) AS v1_rows FROM master_patient_profile_v1;",
        "SELECT COUNT(DISTINCT patient_id) AS distinct_patient_id FROM master_patient_profile_v1;",
        "SELECT COUNT(DISTINCT crm_patient_code) AS distinct_crm_code FROM master_patient_profile_v1;",
        "SELECT SUM(payment_rows_count) AS payment_rows_covered FROM master_patient_profile_v1;",
        "SELECT COUNT(*) AS review_queue_rows FROM master_patient_profile_review_queue;",
        "SELECT COUNT(*) AS total_payment_rows_with_code FROM payments_crm_code_all_years",
        "  WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> '';",
        "SELECT (SELECT SUM(payment_rows_count) FROM master_patient_profile_v1) * 100.0 / NULLIF(",
        "  (SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''), 0) AS coverage_pct;",
        "```",
        "",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {report_path}")
    print(f"  V1 rows: {v1_rows:,}  |  Review queue: {review_rows:,}  |  Payment coverage: {pct_covered:.2f}%")


if __name__ == "__main__":
    main()
