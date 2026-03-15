# -*- coding: utf-8 -*-
"""
Regenerate CRM Code → Patient Link report from existing link tables.
Run after build_crm_code_patient_links.py. Does not modify any tables.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    try:
        n_promoted = conn.execute("SELECT COUNT(*) FROM crm_code_patient_link_promoted").fetchone()[0]
        distinct_patients = conn.execute(
            "SELECT COUNT(DISTINCT patient_id) FROM crm_code_patient_link_promoted"
        ).fetchone()[0]
        n_ambiguous_rows = conn.execute("SELECT COUNT(*) FROM crm_code_patient_link_ambiguous").fetchone()[0]
        n_ambiguous_codes = conn.execute(
            "SELECT COUNT(DISTINCT crm_patient_code) FROM crm_code_patient_link_ambiguous"
        ).fetchone()[0]
    except sqlite3.OperationalError as e:
        print(f"Link tables missing? {e}")
        conn.close()
        sys.exit(1)

    total_with_code = conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''"
    ).fetchone()[0]
    linked_rows = conn.execute(
        "SELECT COALESCE(SUM(payment_rows_count), 0) FROM crm_code_patient_link_promoted"
    ).fetchone()[0]
    coverage_pct = (linked_rows / total_with_code * 100) if total_with_code else 0

    lines = [
        "# CRM Code → Patient Link Report",
        "",
        "Bridge between CRM financial identity (crm_patient_code) and patients table.",
        "Linking uses: patient_name_key (exact), phone_primary_norm / phone_all_norm.",
        "",
        "## Outputs",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| CRM codes linked to patients (promoted) | {n_promoted:,} |",
        f"| Patient entities recovered (distinct patient_id in promoted) | {distinct_patients:,} |",
        f"| Ambiguity rows (multiple patients per code) | {n_ambiguous_rows:,} |",
        f"| Ambiguous CRM codes (distinct) | {n_ambiguous_codes:,} |",
        f"| Payment rows with extracted code (denominator) | {total_with_code:,} |",
        f"| Payment rows linked to promoted patients | {linked_rows:,} |",
        f"| Coverage (financial rows linked to patient entities) | {coverage_pct:.2f}% |",
        "",
        "## Confidence tiers",
        "",
    ]
    for tier in ("high", "medium", "low"):
        n = conn.execute(
            "SELECT COUNT(*) FROM crm_code_patient_link_promoted WHERE confidence_tier = ?", (tier,)
        ).fetchone()[0]
        lines.append(f"- **{tier}:** {n:,} links")
    lines.append("")

    report_path = REPO / "docs" / "reports" / "crm_code_patient_link_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {report_path}")
    conn.close()


if __name__ == "__main__":
    main()
