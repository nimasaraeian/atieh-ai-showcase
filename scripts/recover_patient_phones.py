# -*- coding: utf-8 -*-
"""
Patient Phone Recovery - Phase-based Pipeline.

Phases: lookup -> exact -> appointment_exact -> last8_safe -> rebuild -> metrics
Usage:
  python scripts/recover_patient_phones.py --phase all
  python scripts/recover_patient_phones.py --phase lookup
  python scripts/recover_patient_phones.py --phase exact
  ...
"""

import argparse
import logging
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.name_normalizer import normalize_persian_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Milestones for coverage targets
MILESTONE_BASELINE = 50.0
MILESTONE_APPOINTMENT_EXACT = 65.0
MILESTONE_LAST8_SAFE = 80.0
MILESTONE_TARGET = 90.0

# Last8 safe thresholds: only match when cnt <= MAX_LAST8_COLLISION
# Reduce to 1 if phase_last8_safe hangs (unique-only = fastest).
MAX_LAST8_COLLISION_PAYMENTS = 2
MAX_LAST8_COLLISION_PATIENTS = 2
MAX_LAST8_COLLISION_APPOINTMENTS = 2

# Source ranking for tie-break (higher = better)
SOURCE_RANK = {
    "appointment_bridge:phone_plus_name": 9,
    "payments:name_plus_phone": 8,
    "appointment_bridge:exact_phone": 7,
    "payments:exact_phone": 6,
    "appointment_bridge:exact_name": 5,
    "payments:exact_name": 4,
    "appointment_bridge:phone_last8_safe": 3,
    "payments:phone_last8_safe": 2,
    "patients_direct:direct_phone": 1,
}


def get_db_path() -> Path:
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    p = Path(db_url[len("sqlite:///"):] if db_url.startswith("sqlite:///") else db_url)
    return Path(__file__).resolve().parent.parent / p if not p.is_absolute() else p


def normalize_phone_canonical(raw: str) -> str:
    """
    Professional phone normalization: remove space, dash, slash, dot, parentheses,
    +, 00 and 98 at start. Return digits-only for matching.
    """
    if not raw or not isinstance(raw, str):
        return ""
    s = str(raw).strip()
    for ch in " \t\n\r-/.()\uff08\uff09+":
        s = s.replace(ch, "")
    digits = "".join(c for c in s if c.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("98") and len(digits) >= 10:
        digits = digits[2:]
    return digits


def phone_to_last8(digits: str) -> str:
    return digits[-8:] if len(digits) >= 8 else ""


def ensure_index(conn: sqlite3.Connection, idx_sql: str, name: str = "") -> None:
    try:
        conn.execute(idx_sql)
        conn.commit()
    except sqlite3.OperationalError:
        conn.rollback()


@contextmanager
def phase_timer(phase_name: str):
    t0 = time.perf_counter()
    print("[START] %s" % phase_name)
    try:
        yield
        elapsed = time.perf_counter() - t0
        print("[DONE] %s elapsed=%.2fs" % (phase_name, elapsed))
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print("[FAIL] %s elapsed=%.2fs error=%r" % (phase_name, elapsed, str(e)))
        raise


def run_sql(conn: sqlite3.Connection, sql: str, step_name: str = "") -> None:
    try:
        conn.execute(sql)
        conn.commit()
    except sqlite3.OperationalError as e:
        conn.rollback()
        raise RuntimeError("SQL failed [%s]: %s | SQL: %s" % (step_name, str(e), sql[:200]))


def count_and_log(conn: sqlite3.Connection, table_or_sql: str, label: str) -> int:
    if "SELECT" in table_or_sql.upper():
        c = conn.execute(table_or_sql).fetchone()[0]
    else:
        c = conn.execute("SELECT COUNT(*) FROM %s" % table_or_sql).fetchone()[0]
    print("[COUNT] %s=%d" % (label, c))
    return c


# ---------------------------------------------------------------------------
# SCHEMA INIT (run once before phases)
# ---------------------------------------------------------------------------


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patient_identity_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            candidate_mobile TEXT,
            candidate_landline TEXT,
            candidate_record_no TEXT,
            evidence_name TEXT,
            source TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
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
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_identity_evidence_pid ON patient_identity_evidence(patient_id)",
        "CREATE INDEX IF NOT EXISTS idx_phone_candidates_src ON phone_candidates(source_table, source_row_id)",
    ]:
        ensure_index(conn, idx)
    conn.commit()


# ---------------------------------------------------------------------------
# PHASE 1: LOOKUP
# ---------------------------------------------------------------------------


def phase_lookup(conn: sqlite3.Connection) -> None:
    with phase_timer("phase_lookup"):
        conn.execute("DROP TABLE IF EXISTS patient_lookup_norm")
        conn.execute("""
            CREATE TABLE patient_lookup_norm (
                patient_id INTEGER PRIMARY KEY,
                patient_name_norm TEXT,
                patient_phone_norm TEXT,
                patient_phone_last7 TEXT,
                patient_phone_last8 TEXT
            )
        """)
        phone_map = {
            r[0]: (r[1] or r[2] or "").strip()
            for r in conn.execute(
                "SELECT source_row_id, primary_mobile, landline FROM phone_candidates WHERE source_table='patients'"
            ).fetchall()
        }
        lookup_data = []
        seen_pid = set()
        for (pid, name) in conn.execute("SELECT id, name FROM patients").fetchall():
            if pid in seen_pid:
                continue
            seen_pid.add(pid)
            name_norm = normalize_persian_name(name) if name else ""
            raw = phone_map.get(pid, "")
            digits = normalize_phone_canonical(raw)
            norm = raw
            last7 = digits[-7:] if len(digits) >= 7 else ""
            last8 = phone_to_last8(digits)
            lookup_data.append((pid, name_norm, norm or None, last7 or None, last8 or None))
        conn.executemany(
            "INSERT INTO patient_lookup_norm (patient_id, patient_name_norm, patient_phone_norm, patient_phone_last7, patient_phone_last8) VALUES (?, ?, ?, ?, ?)",
            lookup_data,
        )
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_lookup_norm_phone ON patient_lookup_norm(patient_phone_norm)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_lookup_norm_last8 ON patient_lookup_norm(patient_phone_last8)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_lookup_norm_name ON patient_lookup_norm(patient_name_norm)")
        conn.commit()
        count_and_log(conn, "patient_lookup_norm", "patient_lookup_norm")

        conn.execute("DROP TABLE IF EXISTS arb_name_norm")
        conn.execute("CREATE TABLE arb_name_norm (arb_id INTEGER PRIMARY KEY, patient_name_norm TEXT)")
        try:
            rows = conn.execute("SELECT id, patient_name_raw FROM appointment_recordno_bridge").fetchall()
            if rows:
                conn.executemany(
                    "INSERT INTO arb_name_norm (arb_id, patient_name_norm) VALUES (?, ?)",
                    [(r[0], normalize_persian_name(r[1] or "")) for r in rows],
                )
        except sqlite3.OperationalError:
            pass
        conn.commit()

        conn.execute("DROP TABLE IF EXISTS appointment_phone_helper")
        conn.execute("""
            CREATE TABLE appointment_phone_helper (
                arb_id INTEGER PRIMARY KEY,
                appointment_phone_norm TEXT,
                appointment_phone_last7 TEXT,
                appointment_phone_last8 TEXT,
                record_no TEXT,
                patient_name_raw TEXT
            )
        """)
        try:
            conn.execute("""
                INSERT INTO appointment_phone_helper
                (arb_id, appointment_phone_norm, appointment_phone_last7, appointment_phone_last8, record_no, patient_name_raw)
                SELECT arb.id,
                       COALESCE(NULLIF(TRIM(pc.primary_mobile), ''), NULLIF(TRIM(pc.landline), '')),
                       CASE WHEN LENGTH(REPLACE(REPLACE(REPLACE(COALESCE(pc.primary_mobile, pc.landline)||'',' ',''),'-',''),'+',''))>=7
                            THEN SUBSTR(REPLACE(REPLACE(REPLACE(COALESCE(pc.primary_mobile,pc.landline)||'',' ',''),'-',''),'+',''),-7) END,
                       CASE WHEN LENGTH(REPLACE(REPLACE(REPLACE(COALESCE(pc.primary_mobile, pc.landline)||'',' ',''),'-',''),'+',''))>=8
                            THEN SUBSTR(REPLACE(REPLACE(REPLACE(COALESCE(pc.primary_mobile,pc.landline)||'',' ',''),'-',''),'+',''),-8) END,
                       arb.record_no, arb.patient_name_raw
                FROM appointment_recordno_bridge arb
                JOIN phone_candidates pc ON pc.source_table='appointment_recordno_bridge' AND pc.source_row_id=arb.id
                WHERE pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL
            """)
            ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_aph_last8 ON appointment_phone_helper(appointment_phone_last8)")
        except sqlite3.OperationalError:
            conn.rollback()
        conn.commit()

        conn.execute("DROP TABLE IF EXISTS payments_lookup_norm")
        conn.execute("""
            CREATE TABLE payments_lookup_norm (
                payment_id INTEGER PRIMARY KEY,
                payment_name_norm TEXT,
                payment_phone_norm TEXT,
                payment_phone_last7 TEXT,
                payment_phone_last8 TEXT,
                phone_type TEXT,
                patient_name_raw TEXT,
                phone_raw TEXT
            )
        """)
        try:
            pc_rows = conn.execute(
                "SELECT source_row_id, primary_mobile, landline, phone_type FROM phone_candidates WHERE source_table='stg_payments'"
            ).fetchall()
            pc_pay = {}
            for r in pc_rows:
                mid = (r[1] or "").strip()
                land = (r[2] or "").strip()
                phone_norm = mid or land or ""
                pt = "mobile" if mid else ("landline" if land else None)
                pc_pay[r[0]] = (phone_norm, pt)
            pay_rows = conn.execute("SELECT id, patient_name_raw, phone_raw FROM stg_payments").fetchall()
        except sqlite3.OperationalError:
            pc_pay = {}
            pay_rows = []
        pay_data = []
        for row in pay_rows:
            pid, name_raw, phone_raw = row[0], row[1], (row[2] or "")
            name_norm = normalize_persian_name(name_raw) if name_raw else ""
            phone_norm, ptype = pc_pay.get(pid, ("", None))
            digits = normalize_phone_canonical(phone_norm)
            last7 = digits[-7:] if len(digits) >= 7 else ""
            last8 = phone_to_last8(digits)
            pay_data.append((pid, name_norm, phone_norm or None, last7 or None, last8 or None, ptype, name_raw or "", phone_raw))
        if pay_data:
            conn.executemany(
                "INSERT INTO payments_lookup_norm (payment_id, payment_name_norm, payment_phone_norm, payment_phone_last7, payment_phone_last8, phone_type, patient_name_raw, phone_raw) VALUES (?,?,?,?,?,?,?,?)",
                pay_data,
            )
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_pln_phone ON payments_lookup_norm(payment_phone_norm)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_pln_last8 ON payments_lookup_norm(payment_phone_last8)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_pln_name ON payments_lookup_norm(payment_name_norm)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_appt_bridge_phone ON appointment_recordno_bridge(phone_norm)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_appt_bridge_name ON appointment_recordno_bridge(patient_name_norm)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_appt_bridge_record ON appointment_recordno_bridge(record_no)")
        conn.commit()
        count_and_log(conn, "payments_lookup_norm", "payments_lookup_norm")


# ---------------------------------------------------------------------------
# PHASE 2: EXACT (direct + payments exact)
# ---------------------------------------------------------------------------


def phase_exact(conn: sqlite3.Connection) -> None:
    with phase_timer("phase_exact"):
        conn.execute("DELETE FROM patient_identity_evidence")
        conn.commit()

        run_sql(
            conn,
            """
            INSERT INTO patient_identity_evidence
            (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
            SELECT p.id, pc.primary_mobile, pc.landline, p.name, 'patients_direct', 'direct_phone',
                   CASE WHEN pc.primary_mobile IS NOT NULL AND TRIM(COALESCE(pc.primary_mobile,''))!='' THEN 0.95 ELSE 0.75 END
            FROM phone_candidates pc
            JOIN patients p ON pc.source_table='patients' AND pc.source_row_id=p.id
            WHERE pc.primary_mobile IS NOT NULL OR pc.landline IS NOT NULL
            """,
            "direct_evidence",
        )
        count_and_log(
            conn,
            "SELECT COUNT(*) FROM patient_identity_evidence WHERE source='patients_direct'",
            "evidence_patients_direct",
        )

        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS payments_match_exact_phone
            """,
            "drop_exact_phone",
        )
        run_sql(
            conn,
            """
            CREATE TABLE payments_match_exact_phone AS
            SELECT pln.payment_id, ln.patient_id, pln.payment_phone_norm, pln.payment_name_norm, pln.phone_type, ln.patient_name_norm
            FROM payments_lookup_norm pln
            JOIN patient_lookup_norm ln ON ln.patient_phone_norm=pln.payment_phone_norm
            WHERE pln.payment_phone_norm IS NOT NULL AND TRIM(pln.payment_phone_norm)!=''
            """,
            "payments_match_exact_phone",
        )
        count_and_log(conn, "payments_match_exact_phone", "payments_match_exact_phone")

        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS payments_match_exact_name
            """,
            "drop_exact_name",
        )
        run_sql(
            conn,
            """
            CREATE TABLE payments_match_exact_name AS
            SELECT pln.payment_id, ln.patient_id, pln.payment_phone_norm, pln.payment_name_norm, pln.phone_type
            FROM payments_lookup_norm pln
            JOIN patient_lookup_norm ln ON ln.patient_name_norm=pln.payment_name_norm
            WHERE pln.payment_name_norm IS NOT NULL AND TRIM(pln.payment_name_norm)!=''
              AND ln.patient_name_norm IS NOT NULL AND TRIM(ln.patient_name_norm)!=''
            """,
            "payments_match_exact_name",
        )
        count_and_log(conn, "payments_match_exact_name", "payments_match_exact_name")

        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS payments_match_name_plus_phone
            """,
            "drop_name_plus_phone",
        )
        run_sql(
            conn,
            """
            CREATE TABLE payments_match_name_plus_phone AS
            SELECT pe.payment_id, pe.patient_id, pe.payment_phone_norm, pe.payment_name_norm, pe.phone_type
            FROM payments_match_exact_phone pe
            JOIN payments_match_exact_name pn ON pe.payment_id=pn.payment_id AND pe.patient_id=pn.patient_id
            """,
            "payments_match_name_plus_phone",
        )
        count_and_log(conn, "payments_match_name_plus_phone", "payments_match_name_plus_phone")

        run_sql(
            conn,
            """
            INSERT INTO patient_identity_evidence
            (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
            SELECT m.patient_id,
                   CASE WHEN m.phone_type='mobile' THEN m.payment_phone_norm ELSE NULL END,
                   CASE WHEN m.phone_type='landline' OR m.phone_type IS NULL THEN m.payment_phone_norm ELSE NULL END,
                   pln.patient_name_raw, 'payments', 'exact_phone', 0.88
            FROM payments_match_exact_phone m
            JOIN payments_lookup_norm pln ON pln.payment_id=m.payment_id
            """,
            "payments_exact_phone_evidence",
        )
        run_sql(
            conn,
            """
            INSERT INTO patient_identity_evidence
            (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
            SELECT m.patient_id,
                   CASE WHEN m.phone_type='mobile' THEN m.payment_phone_norm ELSE NULL END,
                   CASE WHEN m.phone_type='landline' OR m.phone_type IS NULL THEN m.payment_phone_norm ELSE NULL END,
                   pln.patient_name_raw, 'payments', 'exact_name', 0.72
            FROM payments_match_exact_name m
            JOIN payments_lookup_norm pln ON pln.payment_id=m.payment_id
            """,
            "payments_exact_name_evidence",
        )
        run_sql(
            conn,
            """
            INSERT INTO patient_identity_evidence
            (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
            SELECT m.patient_id,
                   CASE WHEN m.phone_type='mobile' THEN m.payment_phone_norm ELSE NULL END,
                   CASE WHEN m.phone_type='landline' OR m.phone_type IS NULL THEN m.payment_phone_norm ELSE NULL END,
                   pln.patient_name_raw, 'payments', 'name_plus_phone', 0.92
            FROM payments_match_name_plus_phone m
            JOIN payments_lookup_norm pln ON pln.payment_id=m.payment_id
            """,
            "payments_name_plus_phone_evidence",
        )
        count_and_log(
            conn,
            "SELECT COUNT(*) FROM patient_identity_evidence",
            "patient_identity_evidence_total",
        )


# ---------------------------------------------------------------------------
# PHASE 3: APPOINTMENT_EXACT
# ---------------------------------------------------------------------------


def phase_appointment_exact(conn: sqlite3.Connection) -> None:
    with phase_timer("phase_appointment_exact"):
        with phase_timer("phase_appointment_exact subphase: exact_phone"):
            run_sql(
                conn,
                """
                DROP TABLE IF EXISTS appointment_match_exact_phone
                """,
                "drop_appt_exact_phone",
            )
            run_sql(
                conn,
                """
                CREATE TABLE appointment_match_exact_phone AS
                SELECT aph.arb_id, ln.patient_id, aph.appointment_phone_norm, aph.record_no
                FROM appointment_phone_helper aph
                JOIN patient_lookup_norm ln ON ln.patient_phone_norm = aph.appointment_phone_norm
                WHERE aph.appointment_phone_norm IS NOT NULL AND TRIM(aph.appointment_phone_norm) != ''
                """,
                "appointment_match_exact_phone",
            )
            n = count_and_log(conn, "appointment_match_exact_phone", "appointment_match_exact_phone")
            if n > 0:
                run_sql(
                    conn,
                    """
                    INSERT INTO patient_identity_evidence
                    (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
                    SELECT m.patient_id,
                           aph.appointment_phone_norm, NULL, arb.patient_name_raw,
                           'appointment_bridge', 'exact_phone', 0.90
                    FROM appointment_match_exact_phone m
                    JOIN appointment_phone_helper aph ON aph.arb_id = m.arb_id
                    JOIN appointment_recordno_bridge arb ON arb.id = m.arb_id
                    """,
                    "appointment_exact_phone_evidence",
                )
                count_and_log(
                    conn,
                    "SELECT COUNT(*) FROM patient_identity_evidence WHERE source='appointment_bridge' AND evidence_type='exact_phone'",
                    "evidence_appointment_exact_phone",
                )

        with phase_timer("phase_appointment_exact subphase: exact_name"):
            run_sql(
                conn,
                """
                DROP TABLE IF EXISTS appointment_match_exact_name
                """,
                "drop_appt_exact_name",
            )
            run_sql(
                conn,
                """
                CREATE TABLE appointment_match_exact_name AS
                SELECT arb.id AS arb_id, ln.patient_id, aph.appointment_phone_norm, aph.record_no
                FROM appointment_recordno_bridge arb
                JOIN arb_name_norm an ON an.arb_id = arb.id
                JOIN patient_lookup_norm ln ON ln.patient_name_norm = an.patient_name_norm
                JOIN appointment_phone_helper aph ON aph.arb_id = arb.id
                WHERE an.patient_name_norm IS NOT NULL AND TRIM(an.patient_name_norm) != ''
                  AND ln.patient_name_norm IS NOT NULL AND TRIM(ln.patient_name_norm) != ''
                """,
                "appointment_match_exact_name",
            )
            n = count_and_log(conn, "appointment_match_exact_name", "appointment_match_exact_name")
            if n > 0:
                run_sql(
                    conn,
                    """
                    INSERT INTO patient_identity_evidence
                    (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
                    SELECT m.patient_id,
                           aph.appointment_phone_norm, NULL, arb.patient_name_raw,
                           'appointment_bridge', 'exact_name', 0.75
                    FROM appointment_match_exact_name m
                    JOIN appointment_phone_helper aph ON aph.arb_id = m.arb_id
                    JOIN appointment_recordno_bridge arb ON arb.id = m.arb_id
                    """,
                    "appointment_exact_name_evidence",
                )
                count_and_log(
                    conn,
                    "SELECT COUNT(*) FROM patient_identity_evidence WHERE source='appointment_bridge' AND evidence_type='exact_name'",
                    "evidence_appointment_exact_name",
                )

        with phase_timer("phase_appointment_exact subphase: phone_plus_name"):
            run_sql(
                conn,
                """
                DROP TABLE IF EXISTS appointment_match_phone_plus_name
                """,
                "drop_appt_phone_plus_name",
            )
            run_sql(
                conn,
                """
                CREATE TABLE appointment_match_phone_plus_name AS
                SELECT ae.patient_id, ae.arb_id
                FROM appointment_match_exact_phone ae
                JOIN appointment_match_exact_name an ON ae.patient_id = an.patient_id AND ae.arb_id = an.arb_id
                """,
                "appointment_match_phone_plus_name",
            )
            n = count_and_log(conn, "appointment_match_phone_plus_name", "appointment_match_phone_plus_name")
            if n > 0:
                run_sql(
                    conn,
                    """
                    INSERT INTO patient_identity_evidence
                    (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
                    SELECT m.patient_id,
                           aph.appointment_phone_norm, NULL, arb.patient_name_raw,
                           'appointment_bridge', 'phone_plus_name', 0.93
                    FROM appointment_match_phone_plus_name m
                    JOIN appointment_phone_helper aph ON aph.arb_id = m.arb_id
                    JOIN appointment_recordno_bridge arb ON arb.id = m.arb_id
                    """,
                    "appointment_phone_plus_name_evidence",
                )
                count_and_log(
                    conn,
                    "SELECT COUNT(*) FROM patient_identity_evidence WHERE source='appointment_bridge' AND evidence_type='phone_plus_name'",
                    "evidence_appointment_phone_plus_name",
                )
        count_and_log(conn, "SELECT COUNT(*) FROM patient_identity_evidence", "patient_identity_evidence_total")


# ---------------------------------------------------------------------------
# PHASE 4: LAST8_SAFE
# ---------------------------------------------------------------------------


def phase_last8_safe(conn: sqlite3.Connection) -> None:
    with phase_timer("phase_last8_safe"):
        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS payments_last8_stats
            """,
            "drop_payments_last8_stats",
        )
        run_sql(
            conn,
            """
            CREATE TABLE payments_last8_stats AS
            SELECT payment_phone_last8, COUNT(*) AS cnt
            FROM payments_lookup_norm
            WHERE payment_phone_last8 IS NOT NULL AND TRIM(payment_phone_last8) != '' AND LENGTH(TRIM(payment_phone_last8)) = 8
            GROUP BY payment_phone_last8
            """,
            "payments_last8_stats",
        )
        count_and_log(conn, "payments_last8_stats", "payments_last8_stats")

        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS patients_last8_stats
            """,
            "drop_patients_last8_stats",
        )
        run_sql(
            conn,
            """
            CREATE TABLE patients_last8_stats AS
            SELECT patient_phone_last8, COUNT(*) AS cnt
            FROM patient_lookup_norm
            WHERE patient_phone_last8 IS NOT NULL AND TRIM(patient_phone_last8) != '' AND LENGTH(TRIM(patient_phone_last8)) = 8
            GROUP BY patient_phone_last8
            """,
            "patients_last8_stats",
        )
        count_and_log(conn, "patients_last8_stats", "patients_last8_stats")

        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_payments_last8_stats ON payments_last8_stats(payment_phone_last8)")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_patients_last8_stats ON patients_last8_stats(patient_phone_last8)")

        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS payments_match_phone_last8_safe
            """,
            "drop_payments_match_phone_last8_safe",
        )
        run_sql(
            conn,
            """
            CREATE TABLE payments_match_phone_last8_safe AS
            SELECT pln.payment_id, ln.patient_id, pln.payment_phone_norm, pln.payment_name_norm, pln.phone_type
            FROM payments_lookup_norm pln
            JOIN payments_last8_stats ps ON ps.payment_phone_last8 = pln.payment_phone_last8 AND ps.cnt <= %d
            JOIN patients_last8_stats ls ON ls.patient_phone_last8 = pln.payment_phone_last8 AND ls.cnt <= %d
            JOIN patient_lookup_norm ln ON ln.patient_phone_last8 = pln.payment_phone_last8
            WHERE pln.payment_phone_last8 IS NOT NULL AND TRIM(pln.payment_phone_last8) != '' AND LENGTH(TRIM(pln.payment_phone_last8)) = 8
              AND NOT EXISTS (
                  SELECT 1 FROM payments_match_exact_phone pe
                  WHERE pe.payment_id = pln.payment_id AND pe.patient_id = ln.patient_id
              )
            """
            % (MAX_LAST8_COLLISION_PAYMENTS, MAX_LAST8_COLLISION_PATIENTS),
            "payments_match_phone_last8_safe",
        )
        n = count_and_log(conn, "payments_match_phone_last8_safe", "payments_match_phone_last8_safe")
        if n > 0:
            run_sql(
                conn,
                """
                INSERT INTO patient_identity_evidence
                (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
                SELECT m.patient_id,
                       CASE WHEN m.phone_type='mobile' THEN m.payment_phone_norm ELSE NULL END,
                       CASE WHEN m.phone_type='landline' OR m.phone_type IS NULL THEN m.payment_phone_norm ELSE NULL END,
                       pln.patient_name_raw, 'payments', 'phone_last8_safe', 0.82
                FROM payments_match_phone_last8_safe m
                JOIN payments_lookup_norm pln ON pln.payment_id = m.payment_id
                """,
                "payments_phone_last8_safe_evidence",
            )

        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS appointments_last8_stats
            """,
            "drop_appointments_last8_stats",
        )
        run_sql(
            conn,
            """
            CREATE TABLE appointments_last8_stats AS
            SELECT appointment_phone_last8, COUNT(*) AS cnt
            FROM appointment_phone_helper
            WHERE appointment_phone_last8 IS NOT NULL AND TRIM(appointment_phone_last8) != '' AND LENGTH(TRIM(appointment_phone_last8)) = 8
            GROUP BY appointment_phone_last8
            """,
            "appointments_last8_stats",
        )
        count_and_log(conn, "appointments_last8_stats", "appointments_last8_stats")
        ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_appointments_last8_stats ON appointments_last8_stats(appointment_phone_last8)")

        run_sql(
            conn,
            """
            DROP TABLE IF EXISTS appointment_match_phone_last8_safe
            """,
            "drop_appointment_match_phone_last8_safe",
        )
        run_sql(
            conn,
            """
            CREATE TABLE appointment_match_phone_last8_safe AS
            SELECT aph.arb_id, ln.patient_id, aph.appointment_phone_norm
            FROM appointment_phone_helper aph
            JOIN appointments_last8_stats as1 ON as1.appointment_phone_last8 = aph.appointment_phone_last8 AND as1.cnt <= %d
            JOIN patients_last8_stats ls ON ls.patient_phone_last8 = aph.appointment_phone_last8 AND ls.cnt <= %d
            JOIN patient_lookup_norm ln ON ln.patient_phone_last8 = aph.appointment_phone_last8
            WHERE aph.appointment_phone_last8 IS NOT NULL AND TRIM(aph.appointment_phone_last8) != ''
              AND LENGTH(TRIM(aph.appointment_phone_last8)) = 8
              AND NOT EXISTS (
                  SELECT 1 FROM appointment_match_exact_phone ae
                  WHERE ae.arb_id = aph.arb_id AND ae.patient_id = ln.patient_id
              )
            """
            % (MAX_LAST8_COLLISION_APPOINTMENTS, MAX_LAST8_COLLISION_PATIENTS),
            "appointment_match_phone_last8_safe",
        )
        n = count_and_log(conn, "appointment_match_phone_last8_safe", "appointment_match_phone_last8_safe")
        if n > 0:
            run_sql(
                conn,
                """
                INSERT INTO patient_identity_evidence
                (patient_id, candidate_mobile, candidate_landline, evidence_name, source, evidence_type, confidence)
                SELECT m.patient_id, aph.appointment_phone_norm, NULL, arb.patient_name_raw,
                       'appointment_bridge', 'phone_last8_safe', 0.88
                FROM appointment_match_phone_last8_safe m
                JOIN appointment_phone_helper aph ON aph.arb_id = m.arb_id
                JOIN appointment_recordno_bridge arb ON arb.id = m.arb_id
                """,
                "appointment_phone_last8_safe_evidence",
            )
        count_and_log(conn, "SELECT COUNT(*) FROM patient_identity_evidence", "patient_identity_evidence_total")


# ---------------------------------------------------------------------------
# PHASE 5: REBUILD (with source ranking)
# ---------------------------------------------------------------------------


def _source_rank_key(source: str, evidence_type: str) -> int:
    k = "%s:%s" % (source, evidence_type)
    return SOURCE_RANK.get(k, 0)


def phase_rebuild(conn: sqlite3.Connection) -> None:
    with phase_timer("phase_rebuild"):
        conn.execute("DROP TABLE IF EXISTS temp_best_mobile")
        conn.execute("DROP TABLE IF EXISTS temp_best_landline")
        conn.execute("DROP TABLE IF EXISTS temp_best_source")
        conn.commit()

        conn.execute("""
            CREATE TEMP TABLE temp_best_mobile AS
            SELECT patient_id, candidate_mobile AS mobile
            FROM (
                SELECT patient_id, candidate_mobile,
                       ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY confidence DESC) AS rn
                FROM patient_identity_evidence
                WHERE candidate_mobile IS NOT NULL AND TRIM(COALESCE(candidate_mobile,'')) != ''
            ) WHERE rn = 1
        """)
        conn.execute("""
            CREATE TEMP TABLE temp_best_landline AS
            SELECT patient_id, candidate_landline AS landline
            FROM (
                SELECT patient_id, candidate_landline,
                       ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY confidence DESC) AS rn
                FROM patient_identity_evidence
                WHERE candidate_landline IS NOT NULL AND TRIM(COALESCE(candidate_landline,'')) != ''
            ) WHERE rn = 1
        """)

        conn.execute("""
            CREATE TEMP TABLE temp_best_source AS
            SELECT patient_id, source AS best_source, evidence_type, confidence
            FROM (
                SELECT patient_id, source, evidence_type, confidence,
                       ROW_NUMBER() OVER (
                           PARTITION BY patient_id
                           ORDER BY confidence DESC,
                                    CASE source
                                        WHEN 'appointment_bridge' THEN
                                            CASE evidence_type
                                                WHEN 'phone_plus_name' THEN 9
                                                WHEN 'exact_phone' THEN 7
                                                WHEN 'exact_name' THEN 5
                                                WHEN 'phone_last8_safe' THEN 3
                                                ELSE 0 END
                                        WHEN 'payments' THEN
                                            CASE evidence_type
                                                WHEN 'name_plus_phone' THEN 8
                                                WHEN 'exact_phone' THEN 6
                                                WHEN 'exact_name' THEN 4
                                                WHEN 'phone_last8_safe' THEN 2
                                                ELSE 0 END
                                        WHEN 'patients_direct' THEN 1
                                        ELSE 0 END
                       ) AS rn
                FROM patient_identity_evidence
            ) WHERE rn = 1
        """)
        conn.commit()

        conn.execute("DELETE FROM patient_phone_recovered")
        conn.execute("""
            INSERT INTO patient_phone_recovered (patient_id, mobile, landline, best_source, confidence, created_at)
            SELECT s.patient_id, m.mobile, l.landline, s.best_source, s.confidence, datetime('now')
            FROM temp_best_source s
            LEFT JOIN temp_best_mobile m ON m.patient_id = s.patient_id
            LEFT JOIN temp_best_landline l ON l.patient_id = s.patient_id
        """)
        conn.commit()
        count_and_log(conn, "patient_phone_recovered", "patient_phone_recovered")


# ---------------------------------------------------------------------------
# PHASE 6: METRICS
# ---------------------------------------------------------------------------


def phase_metrics(conn: sqlite3.Connection) -> None:
    with phase_timer("phase_metrics"):
        total_patients = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        recovered = conn.execute("SELECT COUNT(*) FROM patient_phone_recovered").fetchone()[0]
        coverage = (recovered * 100.0 / total_patients) if total_patients else 0.0

        print("[COUNT] total_patients=%d" % total_patients)
        print("[COUNT] patient_phone_recovered=%d" % recovered)
        print("[COUNT] coverage_percent=%.2f" % coverage)
        if coverage >= MILESTONE_TARGET:
            print("[MILESTONE] target 90%%+ reached")
        elif coverage >= MILESTONE_LAST8_SAFE:
            print("[MILESTONE] last8_safe target 80%%+ reached")
        elif coverage >= MILESTONE_APPOINTMENT_EXACT:
            print("[MILESTONE] appointment_exact target 65%%+ reached")
        elif coverage >= MILESTONE_BASELINE:
            print("[MILESTONE] baseline exact-only ~50%%")
        else:
            print("[MILESTONE] below baseline")

        print("--- evidence by source/type ---")
        for row in conn.execute("""
            SELECT source, evidence_type, COUNT(*) FROM patient_identity_evidence
            GROUP BY source, evidence_type ORDER BY COUNT(*) DESC
        """):
            print("  %s | %s | %d" % (row[0], row[1], row[2]))

        print("--- patients by best_source ---")
        for row in conn.execute("""
            SELECT best_source, COUNT(*) FROM patient_phone_recovered
            GROUP BY best_source ORDER BY COUNT(*) DESC
        """):
            print("  %s | %d" % (row[0] or "NULL", row[1]))

        direct = conn.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_identity_evidence WHERE source='patients_direct'").fetchone()[0]
        by_appt = conn.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_identity_evidence WHERE source='appointment_bridge'").fetchone()[0]
        by_pay = conn.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_identity_evidence WHERE source='payments'").fetchone()[0]
        by_last8_pay = conn.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_identity_evidence WHERE source='payments' AND evidence_type='phone_last8_safe'").fetchone()[0]
        by_last8_appt = conn.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_identity_evidence WHERE source='appointment_bridge' AND evidence_type='phone_last8_safe'").fetchone()[0]

        print("[COUNT] distinct_patients_by_source: direct=%d appointment_bridge=%d payments=%d" % (direct, by_appt, by_pay))
        print("[COUNT] distinct_patients_last8_safe: payments=%d appointment_bridge=%d" % (by_last8_pay, by_last8_appt))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


PHASE_ORDER = ["lookup", "exact", "appointment_exact", "last8_safe", "rebuild", "metrics"]
PHASE_DEPS = {
    "lookup": [],
    "exact": ["lookup"],
    "appointment_exact": ["lookup", "exact"],
    "last8_safe": ["lookup", "exact", "appointment_exact"],
    "rebuild": ["lookup", "exact", "appointment_exact", "last8_safe"],
    "metrics": ["lookup", "exact", "appointment_exact", "last8_safe", "rebuild"],
}


def _phases_to_run(target: str) -> list:
    if target == "all":
        return PHASE_ORDER
    deps = PHASE_DEPS.get(target, [])
    result = []
    for p in PHASE_ORDER:
        if p in deps or p == target:
            result.append(p)
        if p == target:
            break
    return result


def run_recovery(db_path: Path, phase: str) -> None:
    conn = sqlite3.connect(str(db_path), timeout=120)
    try:
        ensure_schema(conn)
        to_run = _phases_to_run(phase)
        phase_fns = {
            "lookup": phase_lookup,
            "exact": phase_exact,
            "appointment_exact": phase_appointment_exact,
            "last8_safe": phase_last8_safe,
            "rebuild": phase_rebuild,
            "metrics": phase_metrics,
        }
        for p in to_run:
            phase_fns[p](conn)
    except Exception as e:
        logger.exception("Pipeline failed: %s", str(e))
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Patient Phone Recovery - Phase-based Pipeline")
    parser.add_argument("--phase", required=True, choices=["all", "lookup", "exact", "appointment_exact", "last8_safe", "rebuild", "metrics"])
    args = parser.parse_args()
    db_path = get_db_path()
    if not db_path.exists():
        logger.error("Database not found: %s", db_path)
        sys.exit(1)
    run_recovery(db_path, args.phase)
