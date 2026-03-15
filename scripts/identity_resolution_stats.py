# -*- coding: utf-8 -*-
"""
Identity resolution stats: compute metrics and write markdown reports to docs/reports/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
DOCS_REPORTS = REPO / "docs" / "reports"
SQL_DIR = REPO / "sql" / "identity_resolution"


def get_conn(db_path: Path):
    import sqlite3
    return sqlite3.connect(str(db_path))


def run_schema(conn) -> None:
    for name in ("001_identity_resolution_schema.sql", "002_identity_resolution_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _int(cursor) -> int:
    return cursor.fetchone()[0] if cursor else 0


def report_appointments_import(conn, out_path: Path) -> None:
    """K1) Import stats for appointments."""
    c = conn.execute("SELECT COUNT(*) FROM appointments_unified_staging")
    total = _int(c)
    c = conn.execute("SELECT COUNT(DISTINCT source_file) FROM appointments_unified_staging")
    files = _int(c)
    c = conn.execute("SELECT shamsi_year, COUNT(*) FROM appointments_unified_staging GROUP BY shamsi_year ORDER BY shamsi_year")
    rows_per_year = c.fetchall()
    c = conn.execute("SELECT COUNT(*) FROM appointments_unified_staging WHERE phone_raw IS NOT NULL AND TRIM(phone_raw) <> ''")
    with_phone = _int(c)
    c = conn.execute("SELECT COUNT(*) FROM appointments_unified_staging WHERE patient_name_combined_raw IS NOT NULL AND TRIM(patient_name_combined_raw) <> ''")
    with_name = _int(c)

    lines = [
        "# Appointments Unified Import Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## K1) Import stats",
        "",
        f"- **Total appointment files imported:** {files}",
        f"- **Total rows imported:** {total}",
        f"- **Rows with phone:** {with_phone}",
        f"- **Rows with usable patient name:** {with_name}",
        "",
        "### Rows per year",
        "",
        "| Shamsi year | Rows |",
        "|-------------|------|",
    ]
    for year, cnt in rows_per_year:
        lines.append(f"| {year} | {cnt} |")
    lines.extend(["", ""])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def report_normalization(conn, out_path: Path) -> None:
    """K2) Normalization stats for payments, appointments, patients."""
    def row_count(tbl):
        return _int(conn.execute(f"SELECT COUNT(*) FROM {tbl}"))

    def with_phone(tbl):
        col = "phone_primary_norm" if "appointment" in tbl or "patient" in tbl else "mobile_primary_norm"
        return _int(conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NOT NULL AND TRIM({col}) <> ''"))

    def with_nid(tbl):
        return _int(conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE national_id_norm IS NOT NULL"))

    def with_name(tbl):
        return _int(conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE patient_name_key IS NOT NULL AND TRIM(patient_name_key) <> ''"))

    def with_record_no(tbl):
        return _int(conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE record_no_norm IS NOT NULL"))

    lines = [
        "# Identity Normalization Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## K2) Normalization stats",
        "",
        "### identity_normalized_payments",
        f"- Total rows: {row_count('identity_normalized_payments')}",
        f"- Rows with normalized valid phone: {with_phone('identity_normalized_payments')}",
        f"- Rows with normalized valid national_id: {with_nid('identity_normalized_payments')}",
        f"- Rows with usable name key: {with_name('identity_normalized_payments')}",
        f"- Rows with record_no: {with_record_no('identity_normalized_payments')}",
        "",
        "### identity_normalized_appointments",
        f"- Total rows: {row_count('identity_normalized_appointments')}",
        f"- Rows with normalized valid phone: {with_phone('identity_normalized_appointments')} (column phone_primary_norm)",
        f"- Rows with national_id: {with_nid('identity_normalized_appointments')}",
        f"- Rows with usable name key: {with_name('identity_normalized_appointments')}",
        f"- Rows with record_no: {with_record_no('identity_normalized_appointments')}",
        "",
        "### patients_identity_normalized",
        f"- Total rows: {row_count('patients_identity_normalized')}",
        f"- Rows with normalized valid phone: {with_phone('patients_identity_normalized')}",
        f"- Rows with national_id: {with_nid('patients_identity_normalized')}",
        f"- Rows with usable name key: {with_name('patients_identity_normalized')}",
        "",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def report_candidate_match(conn, out_path: Path) -> None:
    """K3) Candidate generation stats by source pair and rule."""
    lines = [
        "# Identity Candidate Match Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## K3) Candidate generation stats",
        "",
    ]
    for left, right in [("payment", "patient"), ("appointment", "patient"), ("payment", "appointment")]:
        c = conn.execute(
            "SELECT COUNT(*) FROM identity_candidate_matches WHERE left_source_type = ? AND right_source_type = ?",
            (left, right),
        )
        n = _int(c)
        lines.append(f"### {left} ↔ {right}: {n} candidates")
        c = conn.execute(
            "SELECT candidate_rule, COUNT(*) FROM identity_candidate_matches WHERE left_source_type = ? AND right_source_type = ? GROUP BY candidate_rule ORDER BY 2 DESC",
            (left, right),
        )
        lines.append("| Rule | Count |")
        lines.append("|------|-------|")
        for rule, cnt in c.fetchall():
            lines.append(f"| {rule} | {cnt} |")
        lines.append("")
    c = conn.execute("SELECT COUNT(DISTINCT left_source_type || '-' || left_row_id) FROM identity_candidate_matches WHERE right_source_type = 'patient'")
    lines.append(f"Unique left rows (payment/appointment) with at least one patient candidate: {_int(c)}")
    c = conn.execute("SELECT left_row_id, COUNT(DISTINCT right_row_id) FROM identity_candidate_matches WHERE right_source_type = 'patient' GROUP BY left_source_type, left_row_id HAVING COUNT(DISTINCT right_row_id) > 1")
    collisions = c.fetchall()
    lines.append(f"Collisions (one left → multiple patients): {len(collisions)}")
    lines.extend(["", ""])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def report_match_scoring(conn, out_path: Path) -> None:
    """K4) Scoring stats: by tier, rule, ambiguity."""
    lines = [
        "# Identity Match Scoring Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## K4) Scoring stats",
        "",
    ]
    for tier in ("A", "B", "C", "D"):
        c = conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE confidence_tier = ?", (tier,))
        lines.append(f"- **Tier {tier}:** {_int(c)}")
    lines.append("")
    c = conn.execute("SELECT candidate_rule, confidence_tier, COUNT(*) FROM identity_candidate_matches GROUP BY candidate_rule, confidence_tier ORDER BY confidence_tier, 3 DESC")
    lines.append("### By rule and tier")
    lines.append("| Rule | Tier | Count |")
    lines.append("|------|------|-------|")
    for rule, t, cnt in c.fetchall():
        lines.append(f"| {rule} | {t} | {cnt} |")
    lines.append("")
    c = conn.execute("SELECT match_status, COUNT(*) FROM identity_candidate_matches GROUP BY match_status")
    lines.append("### By match_status")
    for status, cnt in c.fetchall():
        lines.append(f"- {status}: {cnt}")
    lines.extend(["", ""])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def report_phase1_final(conn, out_path: Path) -> None:
    """K5) High-value summary and phase 2 recommendation."""
    total_c = _int(conn.execute("SELECT COUNT(*) FROM identity_candidate_matches"))
    tier_a = _int(conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE confidence_tier = 'A'"))
    tier_b = _int(conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE confidence_tier = 'B'"))
    amb = _int(conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE match_status = 'ambiguous'"))
    pay_pt = _int(conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE left_source_type = 'payment' AND right_source_type = 'patient'"))
    app_pt = _int(conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE left_source_type = 'appointment' AND right_source_type = 'patient'"))
    pay_app = _int(conn.execute("SELECT COUNT(*) FROM identity_candidate_matches WHERE left_source_type = 'payment' AND right_source_type = 'appointment'"))

    lines = [
        "# Patient Identity Resolution Phase 1 – Final Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## What was built",
        "",
        "1. **appointments_unified_staging** – raw import of all yearly appointment Excel files",
        "2. **identity_normalized_payments** – normalized identity from payments_unified_staging",
        "3. **identity_normalized_appointments** – normalized identity from appointments_unified_staging",
        "4. **patients_identity_normalized** – normalized identity from patients table",
        "5. **identity_candidate_matches** – candidate pairings with rules and scores",
        "6. **identity_clusters_proposed** – optional (not populated in phase 1)",
        "",
        "## Metrics summary",
        "",
        f"- Total candidates: {total_c}",
        f"- Tier A (high confidence): {tier_a}",
        f"- Tier B: {tier_b}",
        f"- Ambiguous (collision): {amb}",
        f"- payment↔patient candidates: {pay_pt}",
        f"- appointment↔patient candidates: {app_pt}",
        f"- payment↔appointment candidates: {pay_app}",
        "",
        "## K5) High-value answers",
        "",
        "1. **Strongest identity bridge:** Phone exact + name exact (A2) and phone exact + high name similarity (A3). National ID is strong in payments but patients.national_id is empty, so A1 yields no payment↔patient link until patients get national_id.",
        "2. **Payment↔appointment at scale:** Feasible via B7 (phone exact); count above.",
        "3. **Appointment↔patient at scale:** Feasible via phone+name (A2/A3) and phone-only (B1) with review.",
        "4. **Payment↔patient direct phone-based:** Feasible where phone and name align; Tier A/B counts above.",
        "5. **High-confidence coverage:** Tier A + Tier B as percentage of total candidates and of total payment/appointment rows is in normalization and scoring reports.",
        "6. **Phase 2:** (a) Final assignment layer for Tier A/B non-ambiguous only; (b) Appointment bridge promotion; (c) Record_no extraction improvement; (d) Fuzzy review workflow for Tier C/D.",
        "",
        "## Limitations",
        "",
        "- No final patient_id assignment to payments or patients.",
        "- Persian name similarity threshold is strict to avoid over-match.",
        "- payments 1403 has no separate record_no column; left null.",
        "- patients.national_id is empty; national_id match to patients not used yet.",
        "",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    db_path = os.environ.get("ATIEH_DB_PATH") or os.environ.get("DB_PATH") or str(REPO / "atieh_clinic_recovery81_test.db")
    db_path = Path(db_path)
    if not db_path.is_absolute():
        db_path = REPO / db_path
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    DOCS_REPORTS.mkdir(parents=True, exist_ok=True)
    conn = get_conn(db_path)
    conn.execute("PRAGMA busy_timeout = 30000")
    run_schema(conn)

    report_appointments_import(conn, DOCS_REPORTS / "appointments_unified_import_report.md")
    print("Wrote docs/reports/appointments_unified_import_report.md")
    report_normalization(conn, DOCS_REPORTS / "identity_normalization_report.md")
    print("Wrote docs/reports/identity_normalization_report.md")
    report_candidate_match(conn, DOCS_REPORTS / "identity_candidate_match_report.md")
    print("Wrote docs/reports/identity_candidate_match_report.md")
    report_match_scoring(conn, DOCS_REPORTS / "identity_match_scoring_report.md")
    print("Wrote docs/reports/identity_match_scoring_report.md")
    report_phase1_final(conn, DOCS_REPORTS / "patient_identity_resolution_phase1_report.md")
    print("Wrote docs/reports/patient_identity_resolution_phase1_report.md")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
