# -*- coding: utf-8 -*-
"""
Phase 4: Build phase4_patient_graph_nodes, phase4_patient_graph_edges,
phase4_phone_patient_links, phase4_name_patient_links.
Uses anchor evidence (identity_anchor_*) + patients_identity_normalized + phase2/3 linked rows.
Does NOT update patients or payments.patient_id.
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
    for name in ("010_phase4_graph_propagation_schema.sql", "011_phase4_graph_propagation_indexes.sql"):
        path = SQL_DIR / name
        if path.exists():
            conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def build_phone_links(conn) -> None:
    conn.execute("DELETE FROM phase4_phone_patient_links")
    conn.commit()

    ins = """
        INSERT INTO phase4_phone_patient_links (phone_norm, patient_id, cluster_id, source_type, source_row_id, is_primary, observation_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    # From identity_anchor_phone_phase3 (anchor cluster phones)
    for r in conn.execute("""
        SELECT patient_id, phone_norm, observation_count,
               appears_in_payments_count, appears_in_appointments_count, appears_in_patients_count
        FROM identity_anchor_phone_phase3
    """).fetchall():
        pid, ph, obs = r[0], r[1], r[2]
        if not ph:
            continue
        total_obs = obs + (r[3] or 0) + (r[4] or 0) + (r[5] or 0)
        conn.execute(ins, (ph, pid, pid, "patient", pid, 1, max(1, total_obs)))

    # From patients_identity_normalized (all patients: primary + all)
    for r in conn.execute("""
        SELECT patient_id, phone_primary_norm, phone_all_norm_json FROM patients_identity_normalized
    """).fetchall():
        pid, primary, all_json = r[0], r[1], r[2]
        if primary:
            conn.execute(ins, (primary, pid, None, "patient", pid, 1, 1))
        for ph in _collect_phones(all_json):
            if ph and ph != primary:
                conn.execute(ins, (ph, pid, None, "patient", pid, 0, 1))

    # From phase2 safe + phase3 promoted: payment/appointment rows -> cluster_id
    pay_by_id = {r[0]: r for r in conn.execute("""
        SELECT payments_staging_id, mobile_primary_norm, mobile_all_norm_json FROM identity_normalized_payments
    """).fetchall()}
    app_by_id = {r[0]: r for r in conn.execute("""
        SELECT appointment_staging_id, phone_primary_norm, phone_all_norm_json FROM identity_normalized_appointments
    """).fetchall()}
    for row in conn.execute("""
        SELECT left_source_type, left_row_id, right_row_id FROM safe_identity_matches_phase2 WHERE right_source_type = 'patient'
    """).fetchall():
        src_type, src_id, cluster_id = row
        if src_type == "payment" and src_id in pay_by_id:
            _, prim, all_j = pay_by_id[src_id]
            if prim:
                conn.execute(ins, (prim, cluster_id, cluster_id, "payment", src_id, 1, 1))
            for ph in _collect_phones(all_j):
                if ph:
                    conn.execute(ins, (ph, cluster_id, cluster_id, "payment", src_id, 0, 1))
        elif src_type == "appointment" and src_id in app_by_id:
            _, prim, all_j = app_by_id[src_id]
            if prim:
                conn.execute(ins, (prim, cluster_id, cluster_id, "appointment", src_id, 1, 1))
            for ph in _collect_phones(all_j):
                if ph:
                    conn.execute(ins, (ph, cluster_id, cluster_id, "appointment", src_id, 0, 1))
    try:
        phase3_rows = conn.execute("SELECT source_type, source_row_id, target_patient_id FROM identity_expansion_promoted_phase3").fetchall()
    except Exception:
        phase3_rows = []
    for row in phase3_rows:
        src_type, src_id, cluster_id = row
        if src_type == "payment" and src_id in pay_by_id:
            _, prim, all_j = pay_by_id[src_id]
            if prim:
                conn.execute(ins, (prim, cluster_id, cluster_id, "payment", src_id, 1, 1))
            for ph in _collect_phones(all_j):
                if ph:
                    conn.execute(ins, (ph, cluster_id, cluster_id, "payment", src_id, 0, 1))
        elif src_type == "appointment" and src_id in app_by_id:
            _, prim, all_j = app_by_id[src_id]
            if prim:
                conn.execute(ins, (prim, cluster_id, cluster_id, "appointment", src_id, 1, 1))
            for ph in _collect_phones(all_j):
                if ph:
                    conn.execute(ins, (ph, cluster_id, cluster_id, "appointment", src_id, 0, 1))
    conn.commit()


def build_name_links(conn) -> None:
    conn.execute("DELETE FROM phase4_name_patient_links")
    conn.commit()

    ins = """
        INSERT INTO phase4_name_patient_links (patient_name_key, patient_id, cluster_id, source_type, source_row_id, observation_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    for r in conn.execute("""
        SELECT patient_id, patient_name_key, observation_count FROM identity_anchor_name_phase3
    """).fetchall():
        pid, key, obs = r[0], r[1], r[2]
        if key:
            conn.execute(ins, (key, pid, pid, "patient", pid, max(1, obs)))
    for r in conn.execute("SELECT patient_id, patient_name_key FROM patients_identity_normalized").fetchall():
        pid, key = r[0], r[1]
        if key:
            conn.execute(ins, (key, pid, None, "patient", pid, 1))
    conn.commit()


def build_nodes_and_edges(conn) -> None:
    conn.execute("DELETE FROM phase4_patient_graph_edges")
    conn.execute("DELETE FROM phase4_patient_graph_nodes")
    conn.commit()
    # Minimal node set: one per patient (anchor + unrecovered)
    ins_node = """
        INSERT INTO phase4_patient_graph_nodes (node_type, patient_id, source_type, source_row_id)
        VALUES (?, ?, ?, ?)
    """
    anchor_ids = {r[0] for r in conn.execute("SELECT patient_id FROM identity_anchor_patients_phase3").fetchall()}
    for pid in anchor_ids:
        conn.execute(ins_node, ("anchor_patient", pid, None, None))
    for r in conn.execute("SELECT patient_id FROM patients_identity_normalized").fetchall():
        pid = r[0]
        if pid not in anchor_ids:
            conn.execute(ins_node, ("unrecovered_patient", pid, None, None))
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
    build_nodes_and_edges(conn)
    build_phone_links(conn)
    build_name_links(conn)
    n_phone = conn.execute("SELECT COUNT(*) FROM phase4_phone_patient_links").fetchone()[0]
    n_name = conn.execute("SELECT COUNT(*) FROM phase4_name_patient_links").fetchone()[0]
    print(f"Phone links: {n_phone}, name links: {n_name}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
