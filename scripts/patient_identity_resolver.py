# -*- coding: utf-8 -*-
"""
Patient Identity Resolver - Multi-evidence identity resolution.

Phases:
1. patient_lookup_norm from patients (name + phone normalized)
2. Direct evidence from patients + phone_candidates
3. Appointment bridge evidence (exact phone, exact name, combined)
4. Payments evidence (exact phone, exact name, combined)
5. Aggregate to patient_phone_recovered

All set-based SQL. Minimal Python for lookup population only.
"""

import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.importers.common.normalize import normalize_text
from engine.phone_engine import process as phone_process

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    p = Path(db_url[len("sqlite:///"):] if db_url.startswith("sqlite:///") else db_url)
    return Path(__file__).resolve().parent.parent / p if not p.is_absolute() else p


def _ensure_schema(conn: sqlite3.Connection) -> None:
    mig_dir = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"
    mig_file = mig_dir / "025_patient_identity_resolver.sql"
    if mig_file.exists():
        sql = mig_file.read_text(encoding="utf-8")
        for stmt in [s.strip() for s in sql.split(";") if s.strip() and "DROP TABLE" not in s.upper()]:
            try:
                conn.execute(stmt)
                conn.commit()
            except sqlite3.OperationalError as e:
                if "already exists" in str(e).lower():
                    conn.rollback()
                else:
                    raise
    # Indexes
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_appt_bridge_name ON appointment_recordno_bridge(patient_name_norm)",
        "CREATE INDEX IF NOT EXISTS idx_appt_bridge_phone ON appointment_recordno_bridge(phone_norm)",
        "CREATE INDEX IF NOT EXISTS idx_appt_bridge_record ON appointment_recordno_bridge(record_no)",
        "CREATE INDEX IF NOT EXISTS idx_phone_candidates_src ON phone_candidates(source_table, source_row_id)",
        "CREATE INDEX IF NOT EXISTS idx_patient_identity_evidence_pid ON patient_identity_evidence(patient_id)",
    ]:
        try:
            conn.execute(idx)
            conn.commit()
        except sqlite3.OperationalError:
            conn.rollback()


def _build_patient_lookup_norm(conn: sqlite3.Connection) -> None:
    """Phase 1: patient_lookup_norm from patients + phone_candidates."""
    conn.execute("DELETE FROM patient_lookup_norm")
    # Get normalized phone from phone_candidates
    conn.execute("""
        INSERT INTO patient_lookup_norm (patient_id, patient_name_norm, patient_phone_norm)
        SELECT p.id,
               TRIM(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(COALESCE(p.name,'')), 'ي', 'ی'), 'ك', 'ک'), char(8204), ''), char(8206), '')),
               COALESCE(NULLIF(TRIM(pc.primary_mobile), ''), NULLIF(TRIM(pc.landline), ''))
        FROM patients p
        LEFT JOIN phone_candidates pc ON pc.source_table = 'patients' AND pc.source_row_id = p.id
             AND (pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL)
    """)
    # Override name_norm with proper normalize_text via Python (SQL can't do full Persian norm)
    rows = conn.execute("SELECT patient_id, patient_id FROM patient_lookup_norm").fetchall()
    cur = conn.cursor()
    for (pid,) in conn.execute("SELECT patient_id FROM patient_lookup_norm"):
        name_row = conn.execute("SELECT name FROM patients WHERE id = ?", (pid,)).fetchone()
        name_norm = normalize_text(name_row[0]) if name_row and name_row[0] else ""
        cur.execute("UPDATE patient_lookup_norm SET patient_name_norm = ? WHERE patient_id = ?", (name_norm, pid))
    conn.commit()


def run_resolver(db_path: Path) -> None:
    start = time.perf_counter()
    logger.info("start_time=%s", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    conn = sqlite3.connect(db_path, timeout=120)
    conn.execute("PRAGMA journal_mode=WAL")

    _ensure_schema(conn)

    # Ensure patient_phone_recovered has new schema
    conn.execute("DROP TABLE IF EXISTS patient_phone_recovered")
    conn.execute("""
        CREATE TABLE patient_phone_recovered (
            patient_id INTEGER PRIMARY KEY,
            mobile TEXT,
            landline TEXT,
            best_source TEXT,
            confidence REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # Phase 1: patient_lookup_norm
    conn.execute("DELETE FROM patient_lookup_norm")
    lookup_data = []
    for (pid, name, phone) in conn.execute("SELECT id, name, phone FROM patients"):
        name_norm = normalize_text(name) if name else ""
        phone_norm = None
        if phone:
            r = phone_process(phone)
            phone_norm = r.get("primary_mobile") or r.get("landline")
        lookup_data.append((pid, name_norm, phone_norm))
    conn.executemany(
        "INSERT INTO patient_lookup_norm (patient_id, patient_name_norm, patient_phone_norm) VALUES (?, ?, ?)",
        lookup_data,
    )
    conn.commit()
    logger.info("patient_lookup_norm populated")

    # Clear evidence
    conn.execute("DELETE FROM patient_identity_evidence")
    conn.commit()

    # Phase 2: Direct evidence
    conn.execute("""
        INSERT INTO patient_identity_evidence
        (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
        SELECT p.id, pc.primary_mobile, pc.landline, p.name,
               'patients_direct', 'direct_phone',
               CASE WHEN pc.primary_mobile IS NOT NULL AND TRIM(pc.primary_mobile) != '' THEN 0.95 ELSE 0.75 END
        FROM phone_candidates pc
        JOIN patients p ON pc.source_table = 'patients' AND pc.source_row_id = p.id
        WHERE pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL
    """)
    direct_rows = conn.total_changes
    conn.commit()

    # Phase 3A: Appointment bridge exact phone
    conn.execute("""
        INSERT INTO patient_identity_evidence
        (patient_id, candidate_mobile, candidate_landline, candidate_record_no, evidence_name, source, evidence_type, confidence)
        SELECT ln.patient_id, pc.primary_mobile, pc.landline, arb.record_no, arb.patient_name_raw,
               'appointment_bridge', 'exact_phone', 0.93
        FROM phone_candidates pc
        JOIN appointment_recordno_bridge arb ON arb.id = pc.source_row_id
        JOIN patient_lookup_norm ln ON ln.patient_phone_norm = COALESCE(NULLIF(TRIM(pc.primary_mobile),''), NULLIF(TRIM(pc.landline),''))
        WHERE pc.source_table = 'appointment_recordno_bridge'
          AND (pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL)
          AND COALESCE(NULLIF(TRIM(pc.primary_mobile),''), NULLIF(TRIM(pc.landline),'')) IS NOT NULL
    """)
    appt_phone_rows = conn.total_changes - direct_rows
    appt_phone_rows = conn.total_changes  # cumulative - recalc below
    conn.commit()

    # Phase 3B: Appointment bridge exact name
    conn.execute("""
        INSERT INTO patient_identity_evidence
        (patient_id, candidate_mobile, candidate_landline, candidate_record_no, evidence_name, source, evidence_type, confidence)
        SELECT ln.patient_id, pc.primary_mobile, pc.landline, arb.record_no, arb.patient_name_raw,
               'appointment_bridge', 'exact_name', 0.82
        FROM appointment_recordno_bridge arb
        JOIN phone_candidates pc ON pc.source_table = 'appointment_recordno_bridge' AND pc.source_row_id = arb.id
        JOIN patient_lookup_norm ln ON ln.patient_name_norm = arb.patient_name_norm
             AND arb.patient_name_norm IS NOT NULL AND TRIM(arb.patient_name_norm) != ''
    """)
    appt_name_rows = conn.total_changes
    conn.commit()

    # Phase 3C: Combined (same patient from both phone and name) - insert with 0.97
    # Avoid duplicate: only add combined when we have both matches for same patient from same bridge row
    conn.execute("""
        INSERT INTO patient_identity_evidence
        (patient_id, candidate_mobile, candidate_landline, candidate_record_no, evidence_name, source, evidence_type, confidence)
        SELECT ln.patient_id, pc.primary_mobile, pc.landline, arb.record_no, arb.patient_name_raw,
               'appointment_bridge', 'combined_phone_name', 0.97
        FROM appointment_recordno_bridge arb
        JOIN phone_candidates pc ON pc.source_table = 'appointment_recordno_bridge' AND pc.source_row_id = arb.id
        JOIN patient_lookup_norm ln
          ON ln.patient_phone_norm = COALESCE(NULLIF(TRIM(pc.primary_mobile),''), NULLIF(TRIM(pc.landline),''))
         AND ln.patient_name_norm = arb.patient_name_norm
         AND arb.patient_name_norm IS NOT NULL AND TRIM(arb.patient_name_norm) != ''
         AND (pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL)
    """)
    appt_combined_rows = conn.total_changes - appt_name_rows
    conn.commit()

    # Phase 4: Payments - need normalized names; use temp table
    conn.execute("CREATE TABLE IF NOT EXISTS _pay_norm (stg_id INT PRIMARY KEY, name_norm TEXT, phone_norm TEXT)")
    conn.execute("DELETE FROM _pay_norm")
    pay_rows = conn.execute("SELECT id, patient_name_raw FROM stg_payments").fetchall()
    pc_map = {r[0]: (r[1] or "", r[2] or "") for r in conn.execute(
        "SELECT source_row_id, primary_mobile, landline FROM phone_candidates WHERE source_table='stg_payments'"
    ).fetchall()}
    data = []
    for (sid, name_raw) in pay_rows:
        name_norm = normalize_text(name_raw) if name_raw else ""
        phone_norm = (pc_map.get(sid) or (None, None))
        phone_norm = (phone_norm[0] or phone_norm[1] or "").strip()
        data.append((sid, name_norm, phone_norm))
    conn.executemany("INSERT INTO _pay_norm (stg_id, name_norm, phone_norm) VALUES (?, ?, ?)", data)
    conn.commit()

    before = conn.total_changes
    conn.execute("""
        INSERT INTO patient_identity_evidence
        (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
        SELECT ln.patient_id, pc.primary_mobile, pc.landline, pay.patient_name_raw,
               'payments', 'exact_phone', 0.88
        FROM _pay_norm pn
        JOIN stg_payments pay ON pay.id = pn.stg_id
        JOIN phone_candidates pc ON pc.source_table = 'stg_payments' AND pc.source_row_id = pay.id
        JOIN patient_lookup_norm ln ON ln.patient_phone_norm = pn.phone_norm AND pn.phone_norm != ''
        WHERE pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL
    """)
    pay_phone_rows = conn.total_changes - before
    conn.commit()

    before = conn.total_changes
    conn.execute("""
        INSERT INTO patient_identity_evidence
        (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
        SELECT ln.patient_id, pc.primary_mobile, pc.landline, pay.patient_name_raw,
               'payments', 'exact_name', 0.72
        FROM _pay_norm pn
        JOIN stg_payments pay ON pay.id = pn.stg_id
        JOIN phone_candidates pc ON pc.source_table = 'stg_payments' AND pc.source_row_id = pay.id
        JOIN patient_lookup_norm ln ON ln.patient_name_norm = pn.name_norm
             AND pn.name_norm != '' AND ln.patient_name_norm != ''
    """)
    pay_name_rows = conn.total_changes - before
    conn.commit()

    before = conn.total_changes
    conn.execute("""
        INSERT INTO patient_identity_evidence
        (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
        SELECT ln.patient_id, pc.primary_mobile, pc.landline, pay.patient_name_raw,
               'payments', 'name_plus_phone', 0.92
        FROM _pay_norm pn
        JOIN stg_payments pay ON pay.id = pn.stg_id
        JOIN phone_candidates pc ON pc.source_table = 'stg_payments' AND pc.source_row_id = pay.id
        JOIN patient_lookup_norm ln
          ON ln.patient_phone_norm = pn.phone_norm AND ln.patient_name_norm = pn.name_norm
         AND pn.phone_norm != '' AND pn.name_norm != ''
        WHERE pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL
    """)
    pay_combined_rows = conn.total_changes - before
    conn.commit()

    conn.execute("DROP TABLE IF EXISTS _pay_norm")

    # Recalculate row counts (total_changes is cumulative)
    direct_rows = conn.execute("SELECT COUNT(*) FROM patient_identity_evidence WHERE source='patients_direct'").fetchone()[0]
    appt_phone_rows = conn.execute("SELECT COUNT(*) FROM patient_identity_evidence WHERE source='appointment_bridge' AND evidence_type='exact_phone'").fetchone()[0]
    appt_name_rows = conn.execute("SELECT COUNT(*) FROM patient_identity_evidence WHERE source='appointment_bridge' AND evidence_type='exact_name'").fetchone()[0]
    appt_combined_rows = conn.execute("SELECT COUNT(*) FROM patient_identity_evidence WHERE source='appointment_bridge' AND evidence_type='combined_phone_name'").fetchone()[0]
    pay_phone_rows = conn.execute("SELECT COUNT(*) FROM patient_identity_evidence WHERE source='payments' AND evidence_type='exact_phone'").fetchone()[0]
    pay_name_rows = conn.execute("SELECT COUNT(*) FROM patient_identity_evidence WHERE source='payments' AND evidence_type='exact_name'").fetchone()[0]
    pay_combined_rows = conn.execute("SELECT COUNT(*) FROM patient_identity_evidence WHERE source='payments' AND evidence_type='name_plus_phone'").fetchone()[0]

    distinct_with_evidence = conn.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_identity_evidence").fetchone()[0]

    # Phase 5: Aggregate to patient_phone_recovered (one row per patient, best mobile/landline by confidence)
    conn.execute("""
        INSERT INTO patient_phone_recovered (patient_id, mobile, landline, best_source, confidence, created_at)
        WITH ranked AS (
            SELECT patient_id, candidate_mobile, candidate_landline, source, confidence,
                   ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY confidence DESC) AS rn
            FROM patient_identity_evidence
            WHERE candidate_mobile IS NOT NULL AND TRIM(candidate_mobile) != ''
               OR candidate_landline IS NOT NULL AND TRIM(candidate_landline) != ''
        ),
        best_mob AS (
            SELECT patient_id, candidate_mobile
            FROM (SELECT patient_id, candidate_mobile, ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY confidence DESC) AS rn
                  FROM patient_identity_evidence WHERE candidate_mobile IS NOT NULL AND TRIM(candidate_mobile) != '')
            WHERE rn = 1
        ),
        best_land AS (
            SELECT patient_id, candidate_landline
            FROM (SELECT patient_id, candidate_landline, ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY confidence DESC) AS rn
                  FROM patient_identity_evidence WHERE candidate_landline IS NOT NULL AND TRIM(candidate_landline) != '')
            WHERE rn = 1
        )
        SELECT r.patient_id, bm.candidate_mobile, bl.candidate_landline, r.source, r.confidence, datetime('now')
        FROM ranked r
        LEFT JOIN best_mob bm ON bm.patient_id = r.patient_id
        LEFT JOIN best_land bl ON bl.patient_id = r.patient_id
        WHERE r.rn = 1
    """)
    conn.commit()

    final_recovered = conn.execute("SELECT COUNT(*) FROM patient_phone_recovered").fetchone()[0]
    total_patients = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    coverage = (final_recovered / total_patients * 100) if total_patients else 0.0
    elapsed = time.perf_counter() - start

    logger.info("direct_evidence_rows=%d appointment_exact_phone_rows=%d appointment_exact_name_rows=%d appointment_combined_rows=%d",
                direct_rows, appt_phone_rows, appt_name_rows, appt_combined_rows)
    logger.info("payments_exact_phone_rows=%d payments_exact_name_rows=%d payments_combined_rows=%d",
                pay_phone_rows, pay_name_rows, pay_combined_rows)
    logger.info("distinct_patients_with_evidence=%d final_recovered_patients=%d total_patients=%d final_coverage_percentage=%.1f%% elapsed_seconds=%.2f",
                distinct_with_evidence, final_recovered, total_patients, coverage, elapsed)

    conn.close()

    print("=== Summary ===")
    print("direct_evidence_rows", direct_rows)
    print("appointment_exact_phone_rows", appt_phone_rows)
    print("appointment_exact_name_rows", appt_name_rows)
    print("appointment_combined_rows", appt_combined_rows)
    print("payments_exact_phone_rows", pay_phone_rows)
    print("payments_exact_name_rows", pay_name_rows)
    print("payments_combined_rows", pay_combined_rows)
    print("distinct_patients_with_evidence", distinct_with_evidence)
    print("final_recovered_patients", final_recovered)
    print("total_patients", total_patients)
    print("final_coverage_percentage", f"{coverage:.1f}%")
    print("elapsed_seconds", f"{elapsed:.2f}")


if __name__ == "__main__":
    db_path = get_db_path()
    if not db_path.exists():
        logger.error("Database not found: %s", db_path)
        sys.exit(1)
    run_resolver(db_path)
