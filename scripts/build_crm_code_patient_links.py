# -*- coding: utf-8 -*-
"""
Phase: CRM Code → Patient Linking.
Builds bridge between CRM financial identity (crm_patient_code) and patients table using:
  - patient_name_clean ↔ patient_name_key (exact)
  - phone_primary_norm / phone_all_norm_json
  - repeated payment appearances, year consistency, optional cluster evidence.
Rules: High = name exact + phone; Medium = name exact; Low = phone only. Reject name similarity only.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.helpers.persian_text_normalization import patient_name_key
from scripts.helpers.phone_normalization import normalize_phone_primary_and_all


def _collect_phones_from_json(phone_all_norm_json: str | None) -> set[str]:
    if not phone_all_norm_json:
        return set()
    try:
        out = json.loads(phone_all_norm_json)
        return {x for x in out if x and isinstance(x, str)}
    except Exception:
        return set()


def run_schema(conn: sqlite3.Connection) -> None:
    path = REPO / "sql" / "identity_resolution" / "012_crm_code_patient_link_schema.sql"
    if path.exists():
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def load_crm_codes_with_phones(conn: sqlite3.Connection) -> dict:
    """
    Returns dict: crm_patient_code -> {
        name_key: str,
        phones: set[str],
        payment_rows_count: int,
        first_year: int,
        last_year: int,
    }
    """
    agg = {}
    for row in conn.execute("""
        SELECT crm_patient_code, canonical_patient_name, payment_rows_count, first_year, last_year
        FROM crm_code_financial_aggregate
        WHERE crm_patient_code IS NOT NULL AND TRIM(crm_patient_code) <> ''
    """).fetchall():
        code, canonical_name, count, first_y, last_y = row
        code = (code or "").strip()
        name_key = patient_name_key(canonical_name or "") or ""
        agg[code] = {
            "name_key": name_key,
            "phones": set(),
            "payment_rows_count": count or 0,
            "first_year": first_y,
            "last_year": last_y,
        }

    # Collect phones per code from payments_crm_code_all_years + payments_unified_staging
    for row in conn.execute("""
        SELECT c.extracted_crm_code, s.phone_raw
        FROM payments_crm_code_all_years c
        JOIN payments_unified_staging s ON s.id = c.payment_row_id
        WHERE c.parse_status = 'ok' AND c.extracted_crm_code IS NOT NULL AND TRIM(c.extracted_crm_code) <> ''
    """).fetchall():
        code = (row[0] or "").strip()
        if code not in agg:
            continue
        primary, all_json = normalize_phone_primary_and_all(row[1])
        if primary:
            agg[code]["phones"].add(primary)
        for ph in _collect_phones_from_json(all_json):
            if ph:
                agg[code]["phones"].add(ph)
    return agg


def load_patients_identity(conn: sqlite3.Connection) -> list:
    """Returns list of (patient_id, patient_name_key, phone_primary_norm, phone_all_norm_json)."""
    return conn.execute("""
        SELECT patient_id, patient_name_key, phone_primary_norm, phone_all_norm_json
        FROM patients_identity_normalized
    """).fetchall()


def load_phase4_cluster_support(conn: sqlite3.Connection) -> tuple[set, set]:
    """Returns (name_keys_with_cluster, phone_norms_with_cluster) from phase4 if tables exist."""
    name_keys = set()
    phone_norms = set()
    try:
        for row in conn.execute("SELECT patient_name_key FROM phase4_name_patient_links WHERE patient_name_key IS NOT NULL").fetchall():
            if row[0]:
                name_keys.add(row[0])
        for row in conn.execute("SELECT phone_norm FROM phase4_phone_patient_links WHERE phone_norm IS NOT NULL").fetchall():
            if row[0]:
                phone_norms.add(row[0])
    except sqlite3.OperationalError:
        pass
    return name_keys, phone_norms


def build_candidates(
    crm_data: dict,
    patients: list,
    name_keys_with_cluster: set,
    phone_norms_with_cluster: set,
) -> list[tuple]:
    """
    Returns list of candidate rows:
    (crm_patient_code, patient_id, name_key_match, phone_primary_match, phone_any_match,
     payment_rows_count, first_year, last_year, confidence_tier, match_rule, cluster_support)
    """
    # Index patients by name_key and by phone
    by_name_key = defaultdict(list)
    by_phone_primary = defaultdict(list)
    by_phone_any = defaultdict(list)
    patient_rows = {}
    for (pid, name_k, ph_prim, ph_all_json) in patients:
        name_k = (name_k or "").strip()
        patient_rows[pid] = (name_k, ph_prim, ph_all_json)
        if name_k:
            by_name_key[name_k].append(pid)
        if ph_prim:
            by_phone_primary[ph_prim].append(pid)
        for ph in _collect_phones_from_json(ph_all_json):
            if ph:
                by_phone_any[ph].append(pid)

    candidates = []
    for code, data in crm_data.items():
        name_key = data["name_key"]
        phones = data["phones"]
        payment_rows_count = data["payment_rows_count"]
        first_year = data["first_year"]
        last_year = data["last_year"]

        candidate_patient_ids = set()
        if name_key:
            candidate_patient_ids.update(by_name_key.get(name_key, []))
        for ph in phones:
            candidate_patient_ids.update(by_phone_primary.get(ph, []))
            candidate_patient_ids.update(by_phone_any.get(ph, []))

        for pid in candidate_patient_ids:
            name_k, ph_prim, ph_all_json = patient_rows[pid]
            name_match = 1 if (name_key and name_k == name_key) else 0
            ph_prim_match = 1 if (ph_prim and ph_prim in phones) else 0
            patient_phones = {ph_prim} if ph_prim else set()
            patient_phones |= _collect_phones_from_json(ph_all_json)
            ph_any_match = 1 if (phones & patient_phones) else 0

            # Reject: name similarity only (we don't have similarity; we use exact name_key only)
            # So if no name match and no phone match, skip (shouldn't happen by our candidate set)
            if not name_match and not ph_prim_match and not ph_any_match:
                continue

            # Tier and rule
            if name_match and (ph_prim_match or ph_any_match):
                tier = "high"
                rule = "name_exact+phone"
            elif name_match:
                tier = "medium"
                rule = "name_exact"
            else:
                tier = "low"
                rule = "phone_only"

            cluster_support = 0
            if name_key and name_key in name_keys_with_cluster:
                cluster_support = 1
            if not cluster_support and phones and phone_norms_with_cluster and (phones & phone_norms_with_cluster):
                cluster_support = 1

            candidates.append((
                code, pid, name_match, ph_prim_match, ph_any_match,
                payment_rows_count, first_year, last_year, tier, rule, cluster_support,
            ))
    return candidates


def promote_and_ambiguous(candidates: list[tuple]) -> tuple[list, list]:
    """
    From candidates, produce (promoted_rows, ambiguous_rows).
    promoted: (crm_patient_code, patient_id, confidence_tier, match_rule, payment_rows_count, first_year, last_year)
    ambiguous: (crm_patient_code, patient_id, ambiguity_type, candidate_count)
    """
    by_code = defaultdict(list)
    for c in candidates:
        code, pid, nk, ph_prim, ph_any, pay_count, first_y, last_y, tier, rule, cluster = c
        by_code[code].append((pid, tier, rule, pay_count, first_y, last_y))

    tier_rank = {"high": 3, "medium": 2, "low": 1}
    promoted = []
    ambiguous = []

    for code, code_candidates in by_code.items():
        # Best tier for this code
        best_tier = max(tier_rank.get(c[1], 0) for c in code_candidates)
        best_candidates = [c for c in code_candidates if tier_rank.get(c[1], 0) == best_tier]
        best_tier_name = next((t for t, r in tier_rank.items() if r == best_tier), "low")

        if len(best_candidates) == 0:
            continue
        if len(best_candidates) == 1:
            pid, _, rule, pay_count, first_y, last_y = best_candidates[0]
            promoted.append((code, pid, best_tier_name, rule, pay_count, first_y, last_y))
        else:
            for (pid, _, rule, pay_count, first_y, last_y) in best_candidates:
                ambiguous.append((code, pid, "multiple_patients_per_code", len(code_candidates)))

    return promoted, ambiguous


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    run_schema(conn)

    conn.execute("DELETE FROM crm_code_patient_link_ambiguous")
    conn.execute("DELETE FROM crm_code_patient_link_promoted")
    conn.execute("DELETE FROM crm_code_patient_link_candidates")
    conn.commit()

    print("Loading CRM codes with phones...")
    crm_data = load_crm_codes_with_phones(conn)
    print(f"  {len(crm_data):,} CRM codes from crm_code_financial_aggregate")

    print("Loading patients_identity_normalized...")
    patients = load_patients_identity(conn)
    print(f"  {len(patients):,} patients")

    name_keys_cluster, phone_norms_cluster = load_phase4_cluster_support(conn)
    print(f"  Phase4 cluster: {len(name_keys_cluster):,} name keys, {len(phone_norms_cluster):,} phones")

    print("Building candidates...")
    candidates = build_candidates(crm_data, patients, name_keys_cluster, phone_norms_cluster)
    print(f"  {len(candidates):,} candidate links")

    promoted, ambiguous = promote_and_ambiguous(candidates)
    print(f"  Promoted: {len(promoted):,} | Ambiguous: {len(ambiguous):,}")

    ins_cand = """
        INSERT INTO crm_code_patient_link_candidates (
            crm_patient_code, patient_id, name_key_match, phone_primary_match, phone_any_match,
            payment_rows_count, first_year, last_year, confidence_tier, match_rule, cluster_support
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for c in candidates:
        conn.execute(ins_cand, (
            c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10],
        ))
    conn.commit()

    ins_prom = """
        INSERT INTO crm_code_patient_link_promoted (
            crm_patient_code, patient_id, confidence_tier, match_rule,
            payment_rows_count, first_year, last_year
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    for row in promoted:
        conn.execute(ins_prom, (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
    conn.commit()

    ins_amb = """
        INSERT INTO crm_code_patient_link_ambiguous (crm_patient_code, patient_id, ambiguity_type, candidate_count)
        VALUES (?, ?, ?, ?)
    """
    for row in ambiguous:
        conn.execute(ins_amb, (row[0], row[1], row[2], row[3]))
    conn.commit()

    # Report
    total_with_code = conn.execute(
        "SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''"
    ).fetchone()[0]
    linked_rows = sum(r[4] for r in promoted)  # payment_rows_count
    coverage_pct = (linked_rows / total_with_code * 100) if total_with_code else 0

    report_path = REPO / "docs" / "reports" / "crm_code_patient_link_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
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
        f"| CRM codes linked to patients (promoted) | {len(promoted):,} |",
        f"| Patient entities recovered (distinct patient_id in promoted) | {len(set(r[1] for r in promoted)):,} |",
        f"| Ambiguity rows (multiple patients per code) | {len(ambiguous):,} |",
        f"| Ambiguous CRM codes (distinct) | {len(set(r[0] for r in ambiguous)):,} |",
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
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {report_path}")

    conn.close()


if __name__ == "__main__":
    main()
