# -*- coding: utf-8 -*-
"""
Build master_patient_profile_v2 from payment_identity_master + patient_master_link_v2 + patients_identity_normalized.

Final frontend/backend table: one row per linked (crm_patient_code, patient_id) with display and financial fields.
Does NOT modify source tables.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def run_schema(conn: sqlite3.Connection) -> None:
    path = REPO / "sql" / "identity_resolution" / "014_payment_identity_master_v2_schema.sql"
    if path.exists():
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def main() -> None:
    db_path = REPO / "atieh_clinic_recovery81_test.db"
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    run_schema(conn)

    conn.execute("DELETE FROM master_patient_profile_v2")
    conn.commit()

    # Insert from join: payment_identity_master + patient_master_link_v2 + patients_identity_normalized (for canonical patient name/phone preference)
    conn.execute("""
        INSERT INTO master_patient_profile_v2 (
            patient_id, crm_patient_code,
            patient_name_canonical, patient_name_key, primary_phone, all_phones_json, national_id_norm,
            payment_rows_count, total_net_received, positive_net_received_sum, negative_net_received_sum,
            first_year, last_year, identity_strength_tier, link_tier, link_rule, review_flag, review_reason
        )
        SELECT
            l.patient_id,
            p.crm_patient_code,
            COALESCE(pat.patient_name_norm, p.canonical_patient_name) AS patient_name_canonical,
            COALESCE(pat.patient_name_key, p.patient_name_key) AS patient_name_key,
            COALESCE(pat.phone_primary_norm, p.primary_phone_norm) AS primary_phone,
            COALESCE(pat.phone_all_norm_json, p.all_phones_json) AS all_phones_json,
            COALESCE(pat.national_id_norm, p.canonical_national_id_norm) AS national_id_norm,
            p.payment_rows_count,
            p.total_net_received,
            p.positive_net_received_sum,
            p.negative_net_received_sum,
            p.first_year,
            p.last_year,
            p.identity_strength_tier,
            l.link_tier,
            l.link_rule,
            l.review_flag,
            l.review_reason
        FROM patient_master_link_v2 l
        JOIN payment_identity_master p ON p.crm_patient_code = l.crm_patient_code
        LEFT JOIN patients_identity_normalized pat ON pat.patient_id = l.patient_id
    """)
    conn.commit()

    n = conn.execute("SELECT COUNT(*) FROM master_patient_profile_v2").fetchone()[0]
    print(f"Built master_patient_profile_v2: {n:,} rows")
    conn.close()


if __name__ == "__main__":
    main()
