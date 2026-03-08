# -*- coding: utf-8 -*-
"""
Import multiple history Excel files into the database.
Usage: python scripts/import_history_batch.py
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database import SessionLocal
from app.importers.history_importer import import_history_excel

FILES = [
    ("data/inputs/history/1395/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1395.xlsx", 1395),
    ("data/inputs/history/1396/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1396.xlsx", 1396),
    ("data/inputs/history/1398/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1398.xlsx", 1398),
    ("data/inputs/history/1399/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1399.xlsx", 1399),
    ("data/inputs/history/1400/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1400.xlsx", 1400),
    ("data/inputs/history/1401/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1401.xlsx", 1401),
    ("data/inputs/history/1402/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1402.xlsx", 1402),
    ("data/inputs/history/1403/نوبت_دهی_بیمارانی_که_حضور_پیدا_کردند_1403.xlsx", 1403),
    ("data/inputs/history/1404/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx", 1404),
]


def main():
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
            INSERT INTO import_runs (run_type, status, started_at, created_by)
            VALUES (:run_type, :status, :started_at, :created_by)
            """),
            {"run_type": "history", "status": "running", "started_at": datetime.now().isoformat(), "created_by": "batch_script"}
        )
        db.commit()
        import_run_id = result.lastrowid
        print(f"Import run ID: {import_run_id}")

        total_patients = 0
        total_success = 0
        total_errors = 0

        repo_root = Path(__file__).parent.parent
        for file_path, year in FILES:
            p = repo_root / file_path
            if not p.exists():
                print(f"SKIP (not found): {file_path}")
                continue
            print(f"\nImporting year {year}...")
            try:
                stats = import_history_excel(
                    file_path=file_path,
                    import_run_id=import_run_id,
                    sheet_name=0,
                    db=db,
                )
                total_patients += stats.get("patients_created", 0) + stats.get("patients_updated", 0)
                total_success += stats.get("success", 0)
                total_errors += stats.get("errors", 0)
                print(f"  rows={stats.get('total_rows')}, success={stats.get('success')}, errors={stats.get('errors')}, patients_created={stats.get('patients_created')}")
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()

        db.execute(
            text("UPDATE import_runs SET status='success', completed_at=:t WHERE id=:id"),
            {"t": datetime.now().isoformat(), "id": import_run_id}
        )
        db.commit()

        count = db.execute(text("SELECT COUNT(*) FROM patients")).scalar()
        print(f"\nDone. Total patients in DB: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
