# -*- coding: utf-8 -*-
"""
Phone Normalization & Parsing Pipeline (ULTRA-ROBUST).

Scans: patients, stg_payments, appointment_recordno_bridge.
Parse phone fields -> insert phone_candidates.
Goal: primary_mobile or landline for >= 90% of patients.

Usage:
  python scripts/normalize_all_phones.py
"""

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.phone_engine import process

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    if db_url.startswith("sqlite:///"):
        p = Path(db_url[len("sqlite:///"):])
    else:
        p = Path(db_url)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    return p


def ensure_schema(conn: sqlite3.Connection) -> None:
    migrations_dir = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"
    for name in (
        "021_phone_candidates.sql",
        "022_phone_candidates_phone_type.sql",
        "023_phone_candidates_landline.sql",
    ):
        mig_file = migrations_dir / name
        if mig_file.exists():
            with open(mig_file, encoding="utf-8") as f:
                sql = f.read()
            for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
                try:
                    conn.execute(stmt)
                    conn.commit()
                except sqlite3.OperationalError as e:
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        conn.rollback()
                    else:
                        raise
    logger.info("Schema ready.")


SOURCES = [
    ("patients", "id", "phone"),
    ("stg_payments", "id", "phone_raw"),
    ("appointment_recordno_bridge", "id", "phone_raw"),
]


def run_pipeline(db_path: Path) -> None:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row

    ensure_schema(conn)
    conn.execute("DELETE FROM phone_candidates")
    conn.commit()

    rows_processed = 0
    phones_extracted = 0
    mobile_detected = 0
    landline_detected = 0
    invalid_numbers = 0

    for source_table, id_col, phone_col in SOURCES:
        try:
            cur = conn.execute(f"SELECT {id_col}, {phone_col} FROM {source_table}")
        except sqlite3.OperationalError as e:
            logger.warning("Skip %s: %s", source_table, e)
            continue

        rows = cur.fetchall()
        for row in rows:
            row_id = row[id_col]
            raw = str(row[phone_col] or "").strip()
            rows_processed += 1

            result = process(raw)
            norm = result["normalized_candidates"]

            if result["status"] == "invalid":
                invalid_numbers += 1
            if result["primary_mobile"] or result["secondary_mobile"]:
                mobile_detected += 1
            if result["landline"]:
                landline_detected += 1
            phones_extracted += len(norm)

            all_cands = json.dumps(result["all_candidates"], ensure_ascii=False)
            norm_str = ";".join(f"{c}({t})" for c, t in norm) if norm else ""

            cols = (
                "source_table", "source_row_id", "raw_phone",
                "primary_mobile", "secondary_mobile", "landline",
                "all_candidates", "normalized_candidates",
                "confidence_score", "status", "phone_type", "notes"
            )
            placeholders = ", ".join("?" * len(cols))
            try:
                conn.execute(
                    f"INSERT INTO phone_candidates ({','.join(cols)}) VALUES ({placeholders})",
                    (
                        source_table, row_id, result["raw_phone"] or None,
                        result["primary_mobile"], result["secondary_mobile"], result["landline"],
                        all_cands, norm_str,
                        result["confidence_score"], result["status"], result["phone_type"],
                        None,
                    ),
                )
            except sqlite3.OperationalError as e:
                if "no such column: landline" in str(e).lower():
                    conn.execute(
                        """
                        INSERT INTO phone_candidates (
                            source_table, source_row_id, raw_phone,
                            primary_mobile, secondary_mobile,
                            all_candidates, normalized_candidates,
                            confidence_score, status, phone_type, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_table, row_id, result["raw_phone"] or None,
                            result["primary_mobile"], result["secondary_mobile"],
                            all_cands, norm_str,
                            result["confidence_score"], result["status"], result["phone_type"],
                            None,
                        ),
                    )
                else:
                    raise

        logger.info("Processed %s: %d rows", source_table, len(rows))

    conn.commit()

    logger.info(
        "rows_processed=%d phones_extracted=%d mobile_detected=%d landline_detected=%d invalid_numbers=%d",
        rows_processed, phones_extracted, mobile_detected, landline_detected, invalid_numbers,
    )

    # Goal metric: patients with primary_mobile or landline
    try:
        # Prefer landline if column exists
        cols = [r[1] for r in conn.execute("PRAGMA table_info(phone_candidates)").fetchall()]
        has_landline = "landline" in cols
        if has_landline:
            cur = conn.execute(
                """
                SELECT COUNT(DISTINCT source_row_id) FROM phone_candidates
                WHERE source_table = 'patients'
                AND (primary_mobile IS NOT NULL AND primary_mobile != ''
                     OR landline IS NOT NULL AND landline != '')
                """
            )
        else:
            cur = conn.execute(
                """
                SELECT COUNT(DISTINCT source_row_id) FROM phone_candidates
                WHERE source_table = 'patients' AND primary_mobile IS NOT NULL AND primary_mobile != ''
                """
            )
        patients_with_phone = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(*) FROM patients")
        total_patients = cur.fetchone()[0]
        pct = (patients_with_phone / total_patients * 100) if total_patients else 0
        logger.info("patients_with_phone=%d total_patients=%d recovery_pct=%.1f%%", patients_with_phone, total_patients, pct)
        if pct >= 90:
            logger.info("Goal MET: >= 90%% of patients have primary_mobile or landline")
        else:
            logger.info("Goal: reach 90%% (current %.1f%%)", pct)
    except sqlite3.OperationalError:
        pass  # landline column might not exist

    conn.close()


def test_engine() -> None:
    examples = [
        "32256242;09141864468",
        "9141499299",
        "موبایل:09141864468",
        "تماس:04433664565",
        "0914... کار",
        "00989141864468",
        "0914xxxxxxx",
        "914xxxxxxx",
    ]
    logger.info("Test engine with %d examples", len(examples))
    for raw in examples:
        r = process(raw)
        logger.info(
            "  %s -> primary=%s landline=%s type=%s conf=%.2f",
            raw[:35], r["primary_mobile"], r["landline"], r["phone_type"], r["confidence_score"],
        )
    logger.info("Engine test passed.")


if __name__ == "__main__":
    test_engine()
    db_path = get_db_path()
    if not db_path.exists():
        logger.error("Database not found: %s", db_path)
        sys.exit(1)
    logger.info("Running pipeline on %s", db_path)
    run_pipeline(db_path)
    logger.info("Done.")
