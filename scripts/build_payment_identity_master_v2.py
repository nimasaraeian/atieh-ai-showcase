# -*- coding: utf-8 -*-
"""
Build payment_identity_master and payment_identity_master_signals (V2 payments-first model).

One row per financial identity entity (crm_patient_code), aggregated from ALL payment rows.
Uses: payments_crm_code_all_years, payments_unified_staging, payments_national_id_normalized (optional),
crm_code_financial_aggregate. Does NOT modify source tables.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.helpers.persian_text_normalization import (
    patient_name_key,
    patient_name_norm,
    national_id_norm as norm_nid,
    record_no_norm as norm_record_no,
)
from scripts.helpers.phone_normalization import normalize_phone_primary_and_all


def run_schema(conn: sqlite3.Connection) -> None:
    path = REPO / "sql" / "identity_resolution" / "014_payment_identity_master_v2_schema.sql"
    if path.exists():
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _most_frequent(items: list, exclude_blank: bool = True) -> str | None:
    if not items:
        return None
    counts: dict[str, int] = defaultdict(int)
    for x in items:
        v = (x or "").strip() if isinstance(x, str) else str(x or "").strip()
        if exclude_blank and not v:
            continue
        counts[v] += 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _merge_phones_json(jsons: list[str]) -> str:
    seen: set[str] = set()
    for s in jsons:
        if not s:
            continue
        try:
            arr = json.loads(s)
            for x in arr:
                if x and isinstance(x, str) and x not in seen:
                    seen.add(x)
        except Exception:
            continue
    return json.dumps(sorted(seen), ensure_ascii=False) if seen else "[]"


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    run_schema(conn)

    conn.execute("DELETE FROM payment_identity_master_signals")
    conn.execute("DELETE FROM payment_identity_master")
    conn.commit()

    # Load all payment rows with code + staging + optional nid (table may not exist)
    try:
        cur = conn.execute("""
            SELECT c.extracted_crm_code, c.record_no, c.patient_name_clean, c.shamsi_year,
                   s.phone_raw, s.national_id_raw,
                   n.national_id_norm AS nid_norm
            FROM payments_crm_code_all_years c
            JOIN payments_unified_staging s ON s.id = c.payment_row_id
            LEFT JOIN payments_national_id_normalized n ON n.staging_id = c.payment_row_id
            WHERE c.parse_status = 'ok'
              AND c.extracted_crm_code IS NOT NULL AND TRIM(c.extracted_crm_code) <> ''
        """)
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        cur = conn.execute("""
            SELECT c.extracted_crm_code, c.record_no, c.patient_name_clean, c.shamsi_year,
                   s.phone_raw, s.national_id_raw,
                   NULL AS nid_norm
            FROM payments_crm_code_all_years c
            JOIN payments_unified_staging s ON s.id = c.payment_row_id
            WHERE c.parse_status = 'ok'
              AND c.extracted_crm_code IS NOT NULL AND TRIM(c.extracted_crm_code) <> ''
        """)
        rows = cur.fetchall()

    # Financials by code (reuse existing aggregate)
    financial_by_code: dict = {}
    for row in conn.execute(
        "SELECT crm_patient_code, payment_rows_count, total_net_received, positive_net_received_sum, negative_net_received_sum, first_year, last_year FROM crm_code_financial_aggregate"
    ).fetchall():
        financial_by_code[row[0]] = {
            "payment_rows_count": row[1],
            "total_net_received": row[2] or 0,
            "positive_net_received_sum": row[3] or 0,
            "negative_net_received_sum": row[4] or 0,
            "first_year": row[5],
            "last_year": row[6],
        }

    # Aggregate by crm_patient_code
    by_code: dict[str, dict] = defaultdict(lambda: {
        "record_nos": [],
        "names": [],
        "name_keys": [],
        "phones_primary": [],
        "phones_all_json": [],
        "nids": [],
        "years": set(),
        "source_rows": 0,
    })
    # Signals: (crm_code, record_no, name, name_key, phone, nid, year) -> count
    signals_key_counts: dict[tuple, int] = defaultdict(int)

    for row in rows:
        crm_code, record_no_raw, name_clean, shamsi_year, phone_raw, nid_raw, nid_from_table = row
        code = (crm_code or "").strip()
        if not code:
            continue

        name_norm = patient_name_norm(name_clean) if name_clean else ""
        name_key = patient_name_key(name_clean) if name_clean else ""
        primary, all_json = normalize_phone_primary_and_all(phone_raw)
        nid = (nid_from_table or "").strip() if nid_from_table else None
        if not nid and nid_raw is not None:
            nid = norm_nid(nid_raw)
        record_norm = norm_record_no(record_no_raw) or (record_no_raw or "").strip()

        by_code[code]["record_nos"].append(record_norm or None)
        by_code[code]["names"].append(name_norm or None)
        by_code[code]["name_keys"].append(name_key or None)
        if primary:
            by_code[code]["phones_primary"].append(primary)
            by_code[code]["phones_all_json"].append(all_json)
        if nid:
            by_code[code]["nids"].append(nid)
        by_code[code]["years"].add(shamsi_year)
        by_code[code]["source_rows"] += 1

        # Signal key for aggregation (normalize empty to None for grouping)
        sk = (
            code,
            record_norm or None,
            name_norm or None,
            name_key or None,
            primary or None,
            nid,
            shamsi_year,
        )
        signals_key_counts[sk] += 1

    # Insert payment_identity_master
    ins_master = """
        INSERT INTO payment_identity_master (
            crm_patient_code, canonical_record_no, canonical_patient_name, patient_name_key,
            canonical_national_id_norm, primary_phone_norm, all_phones_json,
            payment_rows_count, first_year, last_year,
            total_net_received, positive_net_received_sum, negative_net_received_sum,
            source_rows_count, identity_strength_tier, identity_strength_rule
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for code, data in by_code.items():
        fin = financial_by_code.get(code) or {}
        payment_rows_count = fin.get("payment_rows_count") or data["source_rows"]
        first_year = fin.get("first_year")
        last_year = fin.get("last_year")
        if first_year is None and data["years"]:
            first_year = min(data["years"])
        if last_year is None and data["years"]:
            last_year = max(data["years"])
        total_net = fin.get("total_net_received", 0) or 0
        pos_sum = fin.get("positive_net_received_sum", 0) or 0
        neg_sum = fin.get("negative_net_received_sum", 0) or 0

        canonical_record_no = _most_frequent(data["record_nos"])
        canonical_patient_name = _most_frequent(data["names"])
        patient_name_key_val = _most_frequent(data["name_keys"])
        canonical_national_id_norm = _most_frequent(data["nids"]) if data["nids"] else None
        primary_phone_norm = _most_frequent(data["phones_primary"]) if data["phones_primary"] else None
        all_phones_json = _merge_phones_json(data["phones_all_json"]) if data["phones_all_json"] else "[]"

        has_nid = bool(canonical_national_id_norm)
        has_phone = bool(primary_phone_norm)
        has_name = bool(patient_name_key_val)
        has_record = bool(canonical_record_no)

        if has_nid and (has_phone or has_name):
            identity_strength_tier = "strong"
            identity_strength_rule = "nid+" + ("phone" if has_phone else "name")
        elif sum([has_nid, has_phone, has_name, has_record]) >= 2:
            identity_strength_tier = "medium"
            parts = []
            if has_nid:
                parts.append("nid")
            if has_phone:
                parts.append("phone")
            if has_name:
                parts.append("name")
            if has_record:
                parts.append("record_no")
            identity_strength_rule = "+".join(parts[:2])
        else:
            identity_strength_tier = "weak"
            identity_strength_rule = "crm_only" if not (has_nid or has_phone or has_name) else "single_signal"

        conn.execute(ins_master, (
            code,
            canonical_record_no,
            canonical_patient_name,
            patient_name_key_val,
            canonical_national_id_norm,
            primary_phone_norm,
            all_phones_json,
            payment_rows_count,
            first_year,
            last_year,
            total_net,
            pos_sum,
            neg_sum,
            data["source_rows"],
            identity_strength_tier,
            identity_strength_rule,
        ))
    conn.commit()

    # Insert payment_identity_master_signals
    ins_signal = """
        INSERT INTO payment_identity_master_signals (
            crm_patient_code, observed_record_no, observed_name, observed_name_key,
            observed_phone, observed_national_id, observed_year, observation_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    for (code, rec, name, name_key, phone, nid, year), cnt in signals_key_counts.items():
        conn.execute(ins_signal, (code, rec, name, name_key, phone, nid, year, cnt))
    conn.commit()

    n_master = conn.execute("SELECT COUNT(*) FROM payment_identity_master").fetchone()[0]
    n_signal = conn.execute("SELECT COUNT(*) FROM payment_identity_master_signals").fetchone()[0]
    print(f"Built payment_identity_master: {n_master:,} rows")
    print(f"Built payment_identity_master_signals: {n_signal:,} rows")
    conn.close()


if __name__ == "__main__":
    main()
