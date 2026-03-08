#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrator: run record_no discovery, bridge, map, view; then print validation metrics.
Run from repo root: python tools/run_recordno_resolution_pipeline.py
Options:
  --discover-only   Phase 1 only
  --skip-discover   Skip Phase 1, run bridge + map + validate
  --validate-only  Only run validation queries (after pipeline already run)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "atieh_clinic.db"


def run_cmd(args: list[str]) -> bool:
    r = subprocess.run([sys.executable] + args, cwd=REPO)
    return r.returncode == 0


def ensure_migrations(conn):
    for name in ["013_appointment_recordno_bridge.sql", "014_patient_recordno_map.sql", "015_v_patients_financial_resolved.sql"]:
        mig = REPO / "app" / "db" / "migrations" / name
        if mig.exists():
            with open(mig, encoding="utf-8") as f:
                conn.executescript(f.read())
    conn.commit()


def validate():
    import sqlite3
    if not DB_PATH.exists():
        print("DB not found. Run pipeline first.")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ensure_migrations(conn)

    # 1) Total patients
    total_patients = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]

    # 2) Total distinct record_no in financial data (payments_clean)
    try:
        fin_record_no = cur.execute(
            "SELECT COUNT(DISTINCT record_no) FROM payments_clean WHERE record_no IS NOT NULL AND TRIM(record_no) <> ''"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        fin_record_no = 0

    # 3) Total distinct record_no discovered in appointment files (bridge)
    try:
        appt_record_no = cur.execute(
            "SELECT COUNT(DISTINCT record_no) FROM appointment_recordno_bridge"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        appt_record_no = 0

    # 4) Total patient_id matched to record_no (patient_recordno_map)
    try:
        mapped = cur.execute("SELECT COUNT(*) FROM patient_recordno_map").fetchone()[0]
    except sqlite3.OperationalError:
        mapped = 0

    # 5) Total patients with financial linkage BEFORE (payments_clean.patient_id only)
    before = cur.execute(
        "SELECT COUNT(DISTINCT patient_id) FROM payments_clean WHERE patient_id IS NOT NULL"
    ).fetchone()[0]

    # 6) Total patients with financial linkage AFTER (payments_clean OR patient_recordno_map with financial)
    # From payments_clean
    pids_from_payments = set(
        row[0] for row in cur.execute(
            "SELECT DISTINCT patient_id FROM payments_clean WHERE patient_id IS NOT NULL"
        ).fetchall()
    )
    # From patient_recordno_map where that record_no has financial summary
    try:
        pids_from_map = set(
            row[0] for row in cur.execute("""
                SELECT DISTINCT prm.patient_id
                FROM patient_recordno_map prm
                JOIN patient_financial_summary pfs ON pfs.record_no = prm.record_no
            """).fetchall()
        )
    except sqlite3.OperationalError:
        pids_from_map = set()
    after_ids = pids_from_payments | pids_from_map
    after = len(after_ids)

    # 7) Coverage increase
    increase = after - before if before else after
    pct = (100.0 * increase / before) if before else 100.0

    # 8) Top 20 high-value matched patients (from resolved view)
    try:
        top20 = cur.execute("""
            SELECT patient_id, patient_name, record_no, financial_value, payment_rows, financial_value_score, match_method, confidence
            FROM v_patients_financial_resolved
            WHERE financial_value > 0 OR payment_rows > 0
            ORDER BY financial_value DESC
            LIMIT 20
        """).fetchall()
    except sqlite3.OperationalError:
        top20 = []

    # 9) Top 20 unresolved financial record_no (in payments/financial but not in map)
    try:
        unresolved_fin = cur.execute("""
            SELECT pfs.record_no, pfs.lifetime_net_received, pfs.lifetime_txn_count
            FROM patient_financial_summary pfs
            LEFT JOIN patient_recordno_map prm ON prm.record_no = pfs.record_no
            WHERE prm.record_no IS NULL
            ORDER BY pfs.lifetime_net_received DESC
            LIMIT 20
        """).fetchall()
    except sqlite3.OperationalError:
        unresolved_fin = []

    # 10) Top 20 ambiguous (review table)
    try:
        ambiguous = cur.execute("""
            SELECT record_no, patient_name_norm, candidate_patient_ids, reason
            FROM patient_recordno_map_review
            LIMIT 20
        """).fetchall()
    except sqlite3.OperationalError:
        ambiguous = []

    print()
    print("=" * 70)
    print("PHASE 5 — VALIDATION METRICS")
    print("=" * 70)
    print(f"1. Total patients: {total_patients}")
    print(f"2. Total distinct record_no in financial data (payments_clean): {fin_record_no}")
    print(f"3. Total distinct record_no in appointment bridge: {appt_record_no}")
    print(f"4. Total patient_id mapped to record_no (patient_recordno_map): {mapped}")
    print(f"5. Total patients with financial linkage BEFORE (payments_clean only): {before}")
    print(f"6. Total patients with financial linkage AFTER (payments_clean + record_no map): {after}")
    print(f"7. Coverage increase: +{increase} ({pct:.1f}%)")
    print()
    print("8. Top 20 high-value matched patients (v_patients_financial_resolved):")
    for r in top20:
        print(f"   {r}")
    print()
    print("9. Top 20 unresolved financial record_no (high value, not in map):")
    for r in unresolved_fin:
        print(f"   {r}")
    print()
    print("10. Top 20 ambiguous (patient_recordno_map_review):")
    for r in ambiguous:
        print(f"   {r}")
    conn.close()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--discover-only", action="store_true")
    p.add_argument("--skip-discover", action="store_true")
    p.add_argument("--validate-only", action="store_true")
    args = p.parse_args()

    if args.validate_only:
        validate()
        return 0

    if not args.skip_discover:
        print("Phase 1: Discover record_no in appointment files...")
        if not run_cmd(["tools/discover_recordno_in_appointments.py"]):
            print("Discover failed.")
            return 1
        if args.discover_only:
            return 0

    print("\nPhase 2: Build appointment_recordno_bridge...")
    if not run_cmd(["tools/build_appointment_recordno_bridge.py"]):
        print("Bridge build failed.")
        return 1

    print("\nPhase 3: Build patient_recordno_map...")
    if not run_cmd(["tools/build_patient_recordno_map.py"]):
        print("Map build failed.")
        return 1

    print("\nPhase 4: View v_patients_financial_resolved (migration 015)...")
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    ensure_migrations(conn)
    conn.close()

    print("\nPhase 5: Validation...")
    validate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
