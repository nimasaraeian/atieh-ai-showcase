# -*- coding: utf-8 -*-
"""
Compute validation metrics for payments_crm_code_all_years and write report.
- Per-year: total rows, with code, coverage %, distinct codes, exact match count/rate, null record_no, mismatch count, top mismatches.
- Overall: totals, distinct codes, equality rate, assessment of CRM code as identity key.
- Writes docs/reports/payments_crm_code_all_years_report.md.
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

    # Overall from staging (denominator for coverage)
    total_staging = conn.execute("SELECT COUNT(*) FROM payments_unified_staging").fetchone()[0]
    total_cc = conn.execute("SELECT COUNT(*) FROM payments_crm_code_all_years").fetchone()[0]
    with_code = conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''"
    ).fetchone()[0]
    equals_rec = conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE extracted_code_equals_record_no_flag = 1"
    ).fetchone()[0]
    extracted_but_record_no_null = conn.execute(
        """SELECT COUNT(*) FROM payments_crm_code_all_years
           WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''
           AND (record_no IS NULL OR TRIM(record_no) = '')"""
    ).fetchone()[0]
    mismatch = conn.execute(
        """SELECT COUNT(*) FROM payments_crm_code_all_years
           WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''
           AND record_no IS NOT NULL AND TRIM(record_no) <> ''
           AND extracted_code_equals_record_no_flag = 0"""
    ).fetchone()[0]
    distinct_codes = conn.execute(
        "SELECT COUNT(DISTINCT extracted_crm_code) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''"
    ).fetchone()[0]

    coverage_pct = (with_code / total_staging * 100) if total_staging else 0
    match_rate = (equals_rec / with_code * 100) if with_code else 0

    # Per-year stats
    year_rows = conn.execute(
        """
        SELECT shamsi_year,
               COUNT(*) AS total,
               SUM(CASE WHEN parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> '' THEN 1 ELSE 0 END) AS with_code,
               SUM(CASE WHEN extracted_code_equals_record_no_flag = 1 THEN 1 ELSE 0 END) AS equals_record_no,
               SUM(CASE WHEN parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''
                        AND (record_no IS NULL OR TRIM(record_no) = '') THEN 1 ELSE 0 END) AS code_but_record_no_null,
               SUM(CASE WHEN parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''
                        AND record_no IS NOT NULL AND TRIM(record_no) <> '' AND extracted_code_equals_record_no_flag = 0 THEN 1 ELSE 0 END) AS mismatch
        FROM payments_crm_code_all_years
        GROUP BY shamsi_year
        ORDER BY shamsi_year
        """
    ).fetchall()

    distinct_codes_by_year = {}
    for (year,) in conn.execute(
        "SELECT shamsi_year FROM payments_crm_code_all_years GROUP BY shamsi_year"
    ).fetchall():
        n = conn.execute(
            """SELECT COUNT(DISTINCT extracted_crm_code) FROM payments_crm_code_all_years
               WHERE shamsi_year = ? AND parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''""",
            (year,),
        ).fetchone()[0]
        distinct_codes_by_year[year] = n

    # Top mismatched examples (extracted != record_no, both non-null)
    top_mismatches = conn.execute(
        """
        SELECT patient_name_raw, extracted_crm_code, record_no, shamsi_year
        FROM payments_crm_code_all_years
        WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''
          AND record_no IS NOT NULL AND TRIM(record_no) <> ''
          AND extracted_code_equals_record_no_flag = 0
        ORDER BY shamsi_year
        LIMIT 30
        """
    ).fetchall()

    lines = [
        "# Payments CRM Code All-Years Report",
        "",
        "Identity signal: numeric code inside **final parentheses** in `patient_name_raw` (e.g. `محمودي معصومه(101674)`).",
        "This report validates extraction across all years in `payments_unified_staging` and whether extracted code equals `record_no`.",
        "",
        "---",
        "",
        "## 1. Overall Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total payment rows (staging) | {total_staging:,} |",
        f"| Total rows in CRM layer | {total_cc:,} |",
        f"| Rows with embedded CRM code | {with_code:,} |",
        f"| Coverage (with code / all payment rows) | {coverage_pct:.2f}% |",
        f"| Distinct extracted CRM codes | {distinct_codes:,} |",
        f"| Rows where extracted code = record_no | {equals_rec:,} |",
        f"| Exact match rate (among rows with code) | {match_rate:.2f}% |",
        f"| Rows with code but record_no null | {extracted_but_record_no_null:,} |",
        f"| Rows with code where extracted ≠ record_no | {mismatch:,} |",
        "",
        "---",
        "",
        "## 2. Per-Year Metrics",
        "",
    ]

    for (year, total, with_c, eq_rec, code_null_rec, mism) in year_rows:
        dist = distinct_codes_by_year.get(year, 0)
        cov = (with_c / total * 100) if total else 0
        match_pct = (eq_rec / with_c * 100) if with_c else 0
        lines.extend([
            f"### Shamsi year {year}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total payment rows | {total:,} |",
            f"| Rows with embedded CRM code | {with_c:,} |",
            f"| Coverage % | {cov:.2f}% |",
            f"| Distinct extracted CRM codes | {dist:,} |",
            f"| Rows where extracted = record_no | {eq_rec:,} |",
            f"| Exact match rate % | {match_pct:.2f}% |",
            f"| Rows with code but record_no null | {code_null_rec:,} |",
            f"| Rows where extracted ≠ record_no | {mism:,} |",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 3. Top Mismatched Examples (extracted code ≠ record_no)",
        "",
        "| patient_name_raw | extracted_crm_code | record_no | shamsi_year |",
        "|------------------|--------------------|-----------|-------------|",
    ])
    for (name, ext, rec, y) in top_mismatches:
        name_s = (name or "").replace("|", "\\|")[:60]
        lines.append(f"| {name_s} | {ext or ''} | {rec or ''} | {y} |")
    lines.extend(["", "---", ""])

    # Assessment
    lines.extend([
        "## 4. Assessment",
        "",
    ])
    if with_code > 0:
        if match_rate >= 95:
            lines.append("- **CRM code as identity key:** The extracted code equals `record_no` in the vast majority of rows where both exist. **This is a strong deterministic identity key.**")
        elif match_rate >= 80:
            lines.append("- **CRM code as identity key:** High agreement between extracted code and `record_no`. Suitable as a major resolution signal with validation for mismatches.")
        else:
            lines.append("- **CRM code as identity key:** Moderate agreement. Recommend reviewing mismatches and null record_no cases before treating as primary key.")
    else:
        lines.append("- **CRM code:** No rows with embedded code in the extracted layer; check extraction or source data.")
    lines.append("")
    if with_code > 0 and match_rate >= 90 and distinct_codes > 0:
        lines.append("- **Resolution layer:** This signal is **strong enough to become a major resolution layer**: high coverage of embedded codes, high exact-match rate to `record_no`, and many distinct codes for patient-level aggregation.")
    elif with_code > 0:
        lines.append("- **Resolution layer:** Usable as a supporting resolution layer; consider combining with record_no and other identity signals.")
    lines.append("")

    out_path = REPO / "docs" / "reports" / "payments_crm_code_all_years_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {out_path}")
    conn.close()


if __name__ == "__main__":
    main()
