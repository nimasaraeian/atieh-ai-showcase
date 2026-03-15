# -*- coding: utf-8 -*-
"""
Phase 4: Build expanded cluster evidence from phase2 safe + phase3 promoted links.
Populates identity_cluster_evidence_phase4. Does NOT update patients or payments.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
SQL_DIR = REPO / "sql" / "identity_resolution"


def _collect_phones(s: str | None) -> list[str]:
    if not s:
        return []
    try:
        out = json.loads(s)
        return [x for x in out if x and isinstance(x, str)]
    except Exception:
        return []


def run_schema(conn) -> None:
    for name in ("008_phase4_multihop_propagation_schema.sql", "009_phase4_multihop_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def build_cluster_evidence(conn) -> None:
    conn.execute("DELETE FROM identity_cluster_evidence_phase4")
    conn.commit()

    pay = conn.execute("""
        SELECT payments_staging_id, mobile_primary_norm, mobile_all_norm_json,
               record_no_norm, patient_name_key
        FROM identity_normalized_payments
    """).fetchall()
    pay_by_id = {r[0]: r for r in pay}

    app = conn.execute("""
        SELECT appointment_staging_id, phone_primary_norm, phone_all_norm_json,
               record_no_norm, patient_name_key
        FROM identity_normalized_appointments
    """).fetchall()
    app_by_id = {r[0]: r for r in app}

    pt = conn.execute("""
        SELECT patient_id, phone_primary_norm, phone_all_norm_json, record_no_norm, patient_name_key
        FROM patients_identity_normalized
    """).fetchall()
    pt_by_id = {r[0]: r for r in pt}

    ins = """
        INSERT INTO identity_cluster_evidence_phase4
        (cluster_id, evidence_type, evidence_value, source_origin, source_type, source_row_id, observation_count)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """

    def add_evidence(cluster_id: int, etype: str, value: str, origin: str, src_type: str, row_id: int) -> None:
        if not value or not value.strip():
            return
        conn.execute(ins, (cluster_id, etype, value.strip(), origin, src_type, row_id))

    # Phase2 safe: left -> right_row_id (patient = cluster_id)
    for row in conn.execute("""
        SELECT left_source_type, left_row_id, right_row_id
        FROM safe_identity_matches_phase2 WHERE right_source_type = 'patient'
    """).fetchall():
        src_type, src_id, cluster_id = row
        if src_type == "payment":
            r = pay_by_id.get(src_id)
            if r:
                _, mobile_prim, mobile_all, rec_no, name_k = r
                for ph in ([mobile_prim] if mobile_prim else []) + _collect_phones(mobile_all):
                    add_evidence(cluster_id, "phone", ph, "phase2_safe", "payment", src_id)
                if rec_no:
                    add_evidence(cluster_id, "record_no", rec_no, "phase2_safe", "payment", src_id)
                if name_k:
                    add_evidence(cluster_id, "name_key", name_k, "phase2_safe", "payment", src_id)
        elif src_type == "appointment":
            r = app_by_id.get(src_id)
            if r:
                _, phone_prim, phone_all, rec_no, name_k = r
                for ph in ([phone_prim] if phone_prim else []) + _collect_phones(phone_all):
                    add_evidence(cluster_id, "phone", ph, "phase2_safe", "appointment", src_id)
                if rec_no:
                    add_evidence(cluster_id, "record_no", rec_no, "phase2_safe", "appointment", src_id)
                if name_k:
                    add_evidence(cluster_id, "name_key", name_k, "phase2_safe", "appointment", src_id)

    # Phase3 promoted: source_type, source_row_id -> target_patient_id = cluster_id
    for row in conn.execute("""
        SELECT source_type, source_row_id, target_patient_id
        FROM identity_expansion_promoted_phase3
    """).fetchall():
        src_type, src_id, cluster_id = row
        if src_type == "payment":
            r = pay_by_id.get(src_id)
            if r:
                _, mobile_prim, mobile_all, rec_no, name_k = r
                for ph in ([mobile_prim] if mobile_prim else []) + _collect_phones(mobile_all):
                    add_evidence(cluster_id, "phone", ph, "phase3_promoted", "payment", src_id)
                if rec_no:
                    add_evidence(cluster_id, "record_no", rec_no, "phase3_promoted", "payment", src_id)
                if name_k:
                    add_evidence(cluster_id, "name_key", name_k, "phase3_promoted", "payment", src_id)
        elif src_type == "appointment":
            r = app_by_id.get(src_id)
            if r:
                _, phone_prim, phone_all, rec_no, name_k = r
                for ph in ([phone_prim] if phone_prim else []) + _collect_phones(phone_all):
                    add_evidence(cluster_id, "phone", ph, "phase3_promoted", "appointment", src_id)
                if rec_no:
                    add_evidence(cluster_id, "record_no", rec_no, "phase3_promoted", "appointment", src_id)
                if name_k:
                    add_evidence(cluster_id, "name_key", name_k, "phase3_promoted", "appointment", src_id)

    # Anchor patient's own row (patient-side evidence)
    for row in conn.execute("SELECT patient_id FROM identity_anchor_patients_phase3").fetchall():
        cluster_id = row[0]
        r = pt_by_id.get(cluster_id)
        if r:
            _, phone_prim, phone_all, rec_no, name_k = r
            for ph in ([phone_prim] if phone_prim else []) + _collect_phones(phone_all):
                add_evidence(cluster_id, "phone", ph, "phase2_safe", "patient", cluster_id)
            if rec_no:
                add_evidence(cluster_id, "record_no", rec_no, "phase2_safe", "patient", cluster_id)
            if name_k:
                add_evidence(cluster_id, "name_key", name_k, "phase2_safe", "patient", cluster_id)

    conn.commit()


def main():
    import sqlite3

    db_path = os.environ.get("ATIEH_DB_PATH") or os.environ.get("DB_PATH") or str(REPO / "atieh_clinic_recovery81_test.db")
    db_path = Path(db_path)
    if not db_path.is_absolute():
        db_path = REPO / db_path
    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA busy_timeout = 30000")
    run_schema(conn)
    build_cluster_evidence(conn)
    n = conn.execute("SELECT COUNT(*) FROM identity_cluster_evidence_phase4").fetchone()[0]
    clusters = conn.execute("SELECT COUNT(DISTINCT cluster_id) FROM identity_cluster_evidence_phase4").fetchone()[0]
    print(f"Cluster evidence rows: {n} across {clusters} clusters")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
