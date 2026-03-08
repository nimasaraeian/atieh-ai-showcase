# -*- coding: utf-8 -*-
"""
Database migration runner.

Uses a ``schema_migrations`` table to track which SQL files have already been
applied, so it is fully idempotent – running it multiple times (e.g. on every
server restart) never re-applies a migration or raises an error.
"""
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def get_db_path() -> str:
    """Return the filesystem path to the SQLite database."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    if db_url.startswith("sqlite:///"):
        return db_url[len("sqlite:///"):]
    return db_url


def _open(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def _ensure_tracking_table(conn: sqlite3.Connection) -> None:
    """Create schema_migrations if it does not already exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT    NOT NULL UNIQUE,
            applied_at     TEXT    NOT NULL
        )
    """)
    conn.commit()


def _is_applied(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_name = ?", (name,)
    )
    return cur.fetchone() is not None


def _mark_applied(conn: sqlite3.Connection, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (migration_name, applied_at) VALUES (?, ?)",
        (name, datetime.now().isoformat()),
    )
    conn.commit()


# ── public API ─────────────────────────────────────────────────────────────────

def run_migration(migration_file: Path) -> None:
    """
    Apply a single SQL migration file, executing each statement individually so
    that already-applied DDL (``ALTER TABLE ADD COLUMN``, ``CREATE INDEX``, etc.)
    is silently skipped rather than raising an error.

    The migration is recorded in ``schema_migrations`` on first success.
    """
    db_path = get_db_path()
    logger.info(f"Applying migration: {migration_file.name}")

    with open(migration_file, "r", encoding="utf-8") as fh:
        sql_content = fh.read()

    conn = _open(db_path)
    try:
        _ensure_tracking_table(conn)

        if _is_applied(conn, migration_file.name):
            logger.info(f"Migration already applied, skipping: {migration_file.name}")
            return

        # Execute statement-by-statement so we can swallow idempotent errors.
        # Strip comment-only lines first to avoid empty statements after split.
        clean_lines = [
            line for line in sql_content.splitlines()
            if not line.strip().startswith("--")
        ]
        statements = [
            s.strip()
            for s in "\n".join(clean_lines).split(";")
            if s.strip()
        ]

        applied = skipped = 0
        for stmt in statements:
            try:
                conn.execute(stmt)
                conn.commit()
                applied += 1
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                benign = (
                    "duplicate column name" in msg
                    or "already exists"     in msg
                    or "table already exists" in msg
                )
                if benign:
                    conn.rollback()
                    skipped += 1
                    logger.debug(f"[{migration_file.name}] Skipping (idempotent): {exc}")
                else:
                    logger.error(
                        f"[{migration_file.name}] Statement failed: {exc}\n"
                        f"SQL: {stmt[:120]}"
                    )
                    raise

        _mark_applied(conn, migration_file.name)
        logger.info(
            f"Migration {migration_file.name} completed "
            f"(executed={applied}, skipped={skipped})"
        )

    finally:
        conn.close()


def run_all_migrations() -> None:
    """
    Apply every ``*.sql`` file in ``app/db/migrations/`` in lexicographic order.

    Already-applied migrations are skipped silently.  Safe to call on every
    server startup.
    """
    db_path = get_db_path()
    logger.info(f"Running migrations on: {db_path}")

    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        logger.info("No migration files found.")
        return

    # Bootstrap: mark migrations that are already reflected in the DB schema
    # (e.g. the server was previously running without migration tracking).
    conn = _open(db_path)
    try:
        _ensure_tracking_table(conn)
        _bootstrap_existing(conn, migration_files, db_path)
    finally:
        conn.close()

    for mf in migration_files:
        try:
            run_migration(mf)
        except Exception as exc:
            logger.error(f"Migration {mf.name} failed: {exc}")
            raise

    logger.info(f"All {len(migration_files)} migrations up-to-date.")


def _bootstrap_existing(
    conn: sqlite3.Connection,
    migration_files: list,
    db_path: str,
) -> None:
    """
    Pre-populate ``schema_migrations`` for files whose effects are already in
    the live DB (so we don't re-run them).

    Detection heuristics:
      001_import_pipeline.sql   → stg_appointments table exists
      002_patient_scoring.sql   → patient_priority_score column exists on appointments
      003_payment_normalization.sql → payment_type_norm column exists on appointments
      004_payments_staging.sql  → stg_payments table exists
    """
    _SENTINELS: dict = {
        "001_import_pipeline.sql":        ("table",  "stg_appointments"),
        "002_patient_scoring.sql":        ("column", "appointments", "patient_priority_score"),
        "003_payment_normalization.sql":  ("column", "appointments", "payment_type_norm"),
        "004_payments_staging.sql":       ("table",  "stg_payments"),
        # 005: check that at least one of the two new indexes already exists
        "005_perf_indexes.sql":           ("index",  "idx_appointments_date"),
    }

    for mf in migration_files:
        if _is_applied(conn, mf.name):
            continue

        sentinel = _SENTINELS.get(mf.name)
        if sentinel is None:
            continue

        already_there = False
        if sentinel[0] == "table":
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (sentinel[1],),
            )
            already_there = cur.fetchone() is not None
        elif sentinel[0] == "column":
            _, table, col = sentinel
            cur = conn.execute(f"PRAGMA table_info({table})")
            cols = {row[1] for row in cur.fetchall()}
            already_there = col in cols
        elif sentinel[0] == "index":
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                (sentinel[1],),
            )
            already_there = cur.fetchone() is not None

        if already_there:
            _mark_applied(conn, mf.name)
            logger.info(
                f"Bootstrap: '{mf.name}' effects already present – "
                f"marking as applied without re-running."
            )


def ensure_import_columns() -> None:
    """
    Idempotently add import-related columns to the appointments table.
    Called after ``run_all_migrations()`` for safety.
    """
    db_path = get_db_path()
    conn = _open(db_path)
    try:
        columns_to_add = [
            ("source_row_hash",   "TEXT"),
            ("raw_text_doctor",   "TEXT"),
            ("raw_text_service",  "TEXT"),
            ("raw_text_insurance","TEXT"),
            ("import_run_id",     "INTEGER"),
            ("payment_type_raw",  "TEXT"),
            ("payment_type_norm", "TEXT"),
        ]
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(
                    f"ALTER TABLE appointments ADD COLUMN {col_name} {col_type}"
                )
                conn.commit()
                logger.info(f"Added column appointments.{col_name}")
            except sqlite3.OperationalError:
                conn.rollback()   # column already exists – ignore

        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_source_hash "
                "ON appointments(source_row_hash) WHERE source_row_hash IS NOT NULL"
            )
            conn.commit()
        except sqlite3.OperationalError:
            conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_all_migrations()
    ensure_import_columns()
