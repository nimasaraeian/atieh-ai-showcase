# -*- coding: utf-8 -*-
import os
import sqlite3

DB_PATH = os.getenv("ATIEH_DB_PATH", "atieh_clinic_recovery81_test.db")


def table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,)
    ).fetchone()
    return row is not None


def table_columns(conn, table_name: str):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- output tables: rebuild from scratch
    conn.execute("DROP TABLE IF EXISTS master_patient_profile_v1")
    conn.execute("DROP TABLE IF EXISTS master_patient_profile_review_queue")

    conn.execute("""
    CREATE TABLE master_patient_profile_v1 (
        master_profile_id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        crm_patient_code TEXT NOT NULL,
        patient_name_canonical TEXT,
        patient_name_key TEXT,
        primary_phone TEXT,
        all_phones_json TEXT,
        national_id_norm TEXT,
        payment_rows_count INTEGER,
        total_net_received REAL,
        positive_net_received_sum REAL,
        negative_net_received_sum REAL,
        first_year INTEGER,
        last_year INTEGER,
        link_confidence TEXT,
        link_rule TEXT,
        ambiguity_flag INTEGER NOT NULL DEFAULT 0,
        ambiguity_reason TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    conn.execute("""
    CREATE TABLE master_patient_profile_review_queue (
        review_id INTEGER PRIMARY KEY,
        crm_patient_code TEXT NOT NULL,
        candidate_patient_id INTEGER,
        candidate_name TEXT,
        candidate_phone TEXT,
        ambiguity_reason TEXT,
        candidate_count INTEGER,
        payment_rows_count INTEGER,
        candidate_match_rule TEXT,
        candidate_confidence TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_mpp_v1_patient_id ON master_patient_profile_v1(patient_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mpp_v1_crm_code ON master_patient_profile_v1(crm_patient_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mpp_review_crm_code ON master_patient_profile_review_queue(crm_patient_code)")

    # --- duplication of name_key in patients table
    name_dup = {}
    for r in conn.execute("""
        SELECT patient_name_key, COUNT(*) AS cnt
        FROM patients_identity_normalized
        GROUP BY patient_name_key
    """):
        name_dup[r["patient_name_key"]] = r["cnt"]

    common_name_threshold = 2

    # --- ambiguous CRM codes
    ambiguous_codes = {}
    if table_exists(conn, "crm_code_patient_link_ambiguous"):
        amb_cols = table_columns(conn, "crm_code_patient_link_ambiguous")
        ambiguity_type_col = "ambiguity_type" if "ambiguity_type" in amb_cols else None
        candidate_count_col = "candidate_count" if "candidate_count" in amb_cols else None

        select_parts = ["crm_patient_code"]
        if ambiguity_type_col:
            select_parts.append(f"MAX({ambiguity_type_col}) AS ambiguity_reason")
        else:
            select_parts.append("'ambiguous' AS ambiguity_reason")

        if candidate_count_col:
            select_parts.append(f"MAX({candidate_count_col}) AS candidate_count")
        else:
            select_parts.append("COUNT(*) AS candidate_count")

        sql = f"""
            SELECT {", ".join(select_parts)}
            FROM crm_code_patient_link_ambiguous
            GROUP BY crm_patient_code
        """

        for r in conn.execute(sql):
            ambiguous_codes[r["crm_patient_code"]] = {
                "ambiguity_reason": r["ambiguity_reason"],
                "candidate_count": r["candidate_count"],
            }

        # also push all ambiguous candidates to review queue
        amb_select = """
            SELECT
                a.crm_patient_code,
                a.patient_id AS candidate_patient_id,
                p.patient_name_norm AS candidate_name,
                p.phone_primary_norm AS candidate_phone,
                COALESCE(a.ambiguity_type, 'multiple_patients_per_code') AS ambiguity_reason,
                COALESCE(a.candidate_count, 0) AS candidate_count
            FROM crm_code_patient_link_ambiguous a
            LEFT JOIN patients_identity_normalized p
              ON p.patient_id = a.patient_id
        """

        # if those columns do not exist, use a simpler fallback
        amb_cols = table_columns(conn, "crm_code_patient_link_ambiguous")
        if "ambiguity_type" not in amb_cols or "candidate_count" not in amb_cols:
            amb_select = """
                SELECT
                    a.crm_patient_code,
                    a.patient_id AS candidate_patient_id,
                    p.patient_name_norm AS candidate_name,
                    p.phone_primary_norm AS candidate_phone,
                    'multiple_patients_per_code' AS ambiguity_reason,
                    0 AS candidate_count
                FROM crm_code_patient_link_ambiguous a
                LEFT JOIN patients_identity_normalized p
                  ON p.patient_id = a.patient_id
            """

        amb_rows = conn.execute(amb_select).fetchall()

        conn.executemany("""
            INSERT INTO master_patient_profile_review_queue (
                crm_patient_code,
                candidate_patient_id,
                candidate_name,
                candidate_phone,
                ambiguity_reason,
                candidate_count,
                payment_rows_count,
                candidate_match_rule,
                candidate_confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                r["crm_patient_code"],
                r["candidate_patient_id"],
                r["candidate_name"],
                r["candidate_phone"],
                r["ambiguity_reason"],
                r["candidate_count"],
                None,
                None,
                None
            )
            for r in amb_rows
        ])

    # --- promoted links + patient profile + financial aggregate
    promoted_rows = conn.execute("""
        SELECT
            pr.crm_patient_code,
            pr.patient_id,
            pr.confidence_tier,
            pr.match_rule,
            pr.payment_rows_count AS link_payment_rows_count,
            pr.first_year AS link_first_year,
            pr.last_year AS link_last_year,

            p.patient_name_norm,
            p.patient_name_key,
            p.phone_primary_norm,
            p.phone_all_norm_json,
            p.national_id_norm,

            f.payment_rows_count AS fin_payment_rows_count,
            f.total_net_received,
            f.positive_net_received_sum,
            f.negative_net_received_sum,
            f.first_year AS fin_first_year,
            f.last_year AS fin_last_year,
            f.canonical_patient_name

        FROM crm_code_patient_link_promoted pr
        LEFT JOIN patients_identity_normalized p
          ON p.patient_id = pr.patient_id
        LEFT JOIN crm_code_financial_aggregate f
          ON f.crm_patient_code = pr.crm_patient_code
    """).fetchall()

    safe_count = 0
    review_from_promoted_count = 0

    for r in promoted_rows:
        crm_code = r["crm_patient_code"]
        patient_id = r["patient_id"]
        patient_name_key = r["patient_name_key"]
        patient_name_norm = r["patient_name_norm"]
        phone_primary = r["phone_primary_norm"]

        duplicate_count = name_dup.get(patient_name_key, 0)
        common_name_risky = duplicate_count > common_name_threshold
        has_ambiguity_history = crm_code in ambiguous_codes
        has_financial = r["fin_payment_rows_count"] is not None

        payment_rows_count = r["fin_payment_rows_count"] if r["fin_payment_rows_count"] is not None else r["link_payment_rows_count"]
        first_year = r["fin_first_year"] if r["fin_first_year"] is not None else r["link_first_year"]
        last_year = r["fin_last_year"] if r["fin_last_year"] is not None else r["link_last_year"]

        reasons = []
        if common_name_risky:
            reasons.append(f"common_name_key_dup_gt_{common_name_threshold}")
        if has_ambiguity_history:
            reasons.append("crm_code_has_ambiguity_history")
        if not has_financial:
            reasons.append("missing_financial_aggregate")

        if reasons:
            conn.execute("""
                INSERT INTO master_patient_profile_review_queue (
                    crm_patient_code,
                    candidate_patient_id,
                    candidate_name,
                    candidate_phone,
                    ambiguity_reason,
                    candidate_count,
                    payment_rows_count,
                    candidate_match_rule,
                    candidate_confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                crm_code,
                patient_id,
                patient_name_norm,
                phone_primary,
                "; ".join(reasons),
                duplicate_count if duplicate_count else None,
                payment_rows_count,
                r["match_rule"],
                r["confidence_tier"]
            ))
            review_from_promoted_count += 1
            continue

        conn.execute("""
            INSERT INTO master_patient_profile_v1 (
                patient_id,
                crm_patient_code,
                patient_name_canonical,
                patient_name_key,
                primary_phone,
                all_phones_json,
                national_id_norm,
                payment_rows_count,
                total_net_received,
                positive_net_received_sum,
                negative_net_received_sum,
                first_year,
                last_year,
                link_confidence,
                link_rule,
                ambiguity_flag,
                ambiguity_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            crm_code,
            r["canonical_patient_name"] if r["canonical_patient_name"] is not None else patient_name_norm,
            patient_name_key,
            phone_primary,
            r["phone_all_norm_json"],
            r["national_id_norm"],
            payment_rows_count,
            r["total_net_received"],
            r["positive_net_received_sum"],
            r["negative_net_received_sum"],
            first_year,
            last_year,
            r["confidence_tier"],
            r["match_rule"],
            0,
            None
        ))
        safe_count += 1

    conn.commit()

    v1_rows = conn.execute("SELECT COUNT(*) FROM master_patient_profile_v1").fetchone()[0]
    review_rows = conn.execute("SELECT COUNT(*) FROM master_patient_profile_review_queue").fetchone()[0]

    print(f"Built master_patient_profile_v1: {v1_rows} rows")
    print(f"Built master_patient_profile_review_queue: {review_rows} rows")
    print(f"  Safe promoted kept: {safe_count}")
    print(f"  Promoted moved to review: {review_from_promoted_count}")
    print(f"  Common-name threshold used: > {common_name_threshold}")

    conn.close()


if __name__ == "__main__":
    main()

