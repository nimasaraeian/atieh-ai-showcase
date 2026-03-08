#!/usr/bin/env python3
"""
CLI runner for the payments ingestion pipeline.

Usage examples:
  # Ingest all payment files:
  python scripts/ingest_payments.py

  # Ingest a single year:
  python scripts/ingest_payments.py --year 1404

  # Re-ingest even if already loaded:
  python scripts/ingest_payments.py --force

  # Point at a different DB:
  python scripts/ingest_payments.py --db /path/to/other.db

  # Show distribution query after ingestion:
  python scripts/ingest_payments.py --verify
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

# ── make repo root importable ─────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.importers.payments_importer import (
    PAYMENTS_DIR,
    ingest_all,
    print_summary,
)

DB_PATH = Path(__file__).parent.parent / "atieh_clinic.db"
MIG_FILE = (
    Path(__file__).parent.parent
    / "app" / "db" / "migrations" / "004_payments_staging.sql"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── migration helper ───────────────────────────────────────────────────────────

def ensure_schema(db_path: Path) -> None:
    """Apply migration 004 if stg_payments does not yet exist."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='stg_payments'"
        )
        if cur.fetchone():
            return  # already exists

        logger.info("Creating stg_payments table …")
        with open(MIG_FILE, encoding="utf-8") as f:
            sql = f.read()
        conn.executescript(sql)
        logger.info("stg_payments created.")
    finally:
        conn.close()


# ── post-ingest verification ───────────────────────────────────────────────────

def verify(db_path: Path) -> None:
    """Print per-year distribution from stg_payments."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        print("\n" + "=" * 68)
        print("VERIFICATION: stg_payments distribution by year × payer_source")
        print("=" * 68)

        cur.execute("""
            SELECT
                shamsi_year,
                payer_source_norm,
                COUNT(*)                                           AS cnt,
                SUM(CASE WHEN pct_detected = 1 THEN 1 ELSE 0 END) AS pct_explicit,
                SUM(CASE WHEN pct_detected = 0 AND payer_source_norm = 'insurance'
                         THEN 1 ELSE 0 END)                        AS pct_default_30
            FROM stg_payments
            GROUP BY shamsi_year, payer_source_norm
            ORDER BY shamsi_year, payer_source_norm
        """)
        rows = cur.fetchall()

        if not rows:
            print("  (no rows in stg_payments)")
        else:
            print(
                f"\n  {'Year':<8}  {'Payer':<12}  {'Count':>10}  "
                f"{'Pct explicit':>13}  {'Default 30%':>12}"
            )
            print("  " + "-" * 64)
            for r in rows:
                print(
                    f"  {r['shamsi_year']:<8}  {r['payer_source_norm']:<12}  "
                    f"{r['cnt']:>10,}  {r['pct_explicit']:>13,}  "
                    f"{r['pct_default_30']:>12,}"
                )

        # totals
        cur.execute("SELECT COUNT(*), SUM(pct_detected) FROM stg_payments")
        total, pct_det = cur.fetchone()
        print(f"\n  Total rows   : {total:,}")
        print(f"  Pct detected : {pct_det:,}")
        print("=" * 68 + "\n")

    finally:
        conn.close()


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest payments_<YEAR>_full.xlsx files into stg_payments."
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Only ingest the file for this Shamsi year (e.g. 1404).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest files even if they are already loaded.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help=f"Path to SQLite database (default: {DB_PATH})",
    )
    parser.add_argument(
        "--payments-dir",
        type=Path,
        default=PAYMENTS_DIR,
        help=f"Directory containing payment Excel files (default: {PAYMENTS_DIR})",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Print distribution query after ingestion.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    db_path = args.db.resolve()

    # ── ensure schema ─────────────────────────────────────────────────────────
    ensure_schema(db_path)

    # ── run ingestion ─────────────────────────────────────────────────────────
    file_filter = str(args.year) if args.year else None

    all_stats = ingest_all(
        payments_dir=args.payments_dir,
        db_path=db_path,
        skip_existing=not args.force,
        file_filter=file_filter,
    )

    if not all_stats:
        print("No files processed.")
        return

    print_summary(all_stats)

    if args.verify:
        verify(db_path)


if __name__ == "__main__":
    main()
