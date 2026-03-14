import sqlite3
from datetime import datetime

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic.db"

SOURCE_TABLES = [
    "patients",
    "payments_lookup_norm",
    "appointment_recordno_bridge",
    "appointment_phone_helper",
    "patient_lookup_norm",
]

def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None

def count_rows(cur, table_name: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cur.fetchone()[0]

def clear_phase_metrics(cur):
    cur.execute("""
        DELETE FROM recovery_run_metrics_v2
        WHERE phase_name LIKE 'phase_01_source_validation::%'
    """)

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== Recovery v2 / Phase 01 — Source Validation ===\n")

    clear_phase_metrics(cur)

    total_patients = 0

    for table in SOURCE_TABLES:
        exists = table_exists(cur, table)

        if not exists:
            print(f"[MISSING] {table}")
            cur.execute("""
                INSERT INTO recovery_run_metrics_v2
                (phase_name, total_patients, recovered_count, coverage_percent, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"phase_01_source_validation::{table}",
                total_patients,
                0,
                0.0,
                datetime.now().isoformat(timespec="seconds"),
            ))
            continue

        row_count = count_rows(cur, table)
        print(f"[OK] {table}: {row_count:,} rows")

        if table == "patients":
            total_patients = row_count

        cur.execute("""
            INSERT INTO recovery_run_metrics_v2
            (phase_name, total_patients, recovered_count, coverage_percent, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"phase_01_source_validation::{table}",
            total_patients,
            0,
            0.0,
            datetime.now().isoformat(timespec="seconds"),
        ))

    conn.commit()
    conn.close()

    print("\nPhase 01 completed.\n")

if __name__ == "__main__":
    main()