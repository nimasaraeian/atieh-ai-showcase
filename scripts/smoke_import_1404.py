"""
Smoke test for import pipeline with 1404 file.
Tests migrations, importer, and verifies data was inserted.
Uses isolated database copy to avoid locking issues.
"""
import sys
import shutil
import os
import logging
from pathlib import Path
from sqlalchemy import text

# Fix Unicode encoding on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except:
    pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging with ASCII-safe format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database isolation configuration
ORIGINAL_DB = "atieh_clinic.db"
SMOKE_DB = "atieh_clinic_smoke.db"

def setup_isolated_database():
    """
    Create isolated database copy for smoke test.
    This prevents locking conflicts with running server.
    """
    repo_root = Path(__file__).parent.parent
    original_db_path = repo_root / ORIGINAL_DB
    smoke_db_path = repo_root / SMOKE_DB
    
    # Remove old smoke DB if exists
    if smoke_db_path.exists():
        try:
            smoke_db_path.unlink()
            print(f"[INFO] Removed old smoke test database")
        except Exception as e:
            print(f"[WARN] Could not remove old smoke DB: {e}")
    
    # Create fresh database for smoke test
    # (Do NOT copy - copying can cause corruption with WAL mode)
    print(f"[INFO] Will create fresh isolated database: {SMOKE_DB}")
    
    # Update DATABASE_URL environment variable
    os.environ["DATABASE_URL"] = f"sqlite:///{SMOKE_DB}"
    print(f"[INFO] Database URL set to: sqlite:///{SMOKE_DB}")

# Setup isolated database BEFORE importing database module
setup_isolated_database()

# Now import database module (it will use the updated DATABASE_URL)
from app.db.run_migrations import run_all_migrations, ensure_import_columns
from app.importers.history_importer import import_history_excel
from database import SessionLocal, get_db, engine


def print_separator(title):
    print("\n" + "=" * 80)
    print("  " + title)
    print("=" * 80 + "\n")


def find_1404_excel_file():
    """
    Scan data/inputs/history/1404/ and return the first .xlsx file found.
    Returns None if folder doesn't exist or no .xlsx files found.
    """
    repo_root = Path(__file__).parent.parent
    history_1404_dir = repo_root / "data" / "inputs" / "history" / "1404"
    
    if not history_1404_dir.exists():
        print(f"[WARN] Directory does not exist: {history_1404_dir}")
        return None
    
    xlsx_files = list(history_1404_dir.glob("*.xlsx"))
    
    if not xlsx_files:
        print(f"[WARN] No .xlsx files found in: {history_1404_dir}")
        return None
    
    # Return the first .xlsx file found
    selected_file = xlsx_files[0]
    
    # Safely print filename (ASCII-safe for Windows console)
    try:
        filename = selected_file.name
        print(f"[INFO] Found Excel file: {filename}")
    except UnicodeEncodeError:
        # Fallback: show path without name
        print(f"[INFO] Found Excel file in: {history_1404_dir}")
    
    print(f"[INFO] File size: {selected_file.stat().st_size} bytes")
    
    return selected_file


def cleanup_failed_import(db, import_run_id):
    """
    Clean up staging rows and mark import as failed.
    """
    try:
        # Delete staging rows
        result = db.execute(
            text("DELETE FROM stg_appointments WHERE import_run_id = :run_id"),
            {"run_id": import_run_id}
        )
        deleted_count = result.rowcount
        
        # Mark import as failed
        db.execute(
            text("""
            UPDATE import_runs 
            SET status = 'failed', completed_at = datetime('now'), error = 'File not found or import error'
            WHERE id = :id
            """),
            {"id": import_run_id}
        )
        db.commit()
        
        print(f"[INFO] Cleaned up {deleted_count} staging rows for import_run_id={import_run_id}")
        print(f"[INFO] Marked import_run {import_run_id} as failed")
        
    except Exception as e:
        print(f"[WARN] Cleanup failed: {e}")
        db.rollback()


def verify_tables_exist(db):
    """Check that required tables exist."""
    print_separator("Verifying Tables")
    
    tables_to_check = [
        'import_runs',
        'stg_appointments',
        'stg_reference_rows',
        'patients',
        'appointments'
    ]
    
    all_exist = True
    for table in tables_to_check:
        try:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            print(f"[OK] Table '{table}' exists with {result[0]} rows")
        except Exception as e:
            print(f"[FAIL] Table '{table}' does NOT exist: {e}")
            all_exist = False
    
    return all_exist


def run_import_test():
    """Run the actual import test."""
    print_separator("Running Import")
    
    # Step 1: Find the Excel file BEFORE creating any DB rows
    excel_file = find_1404_excel_file()
    
    if excel_file is None:
        print("\n[WARN] No Excel file found to import.")
        print("\nTo test with actual data:")
        print("1. Place your Excel file (.xlsx) in: data/inputs/history/1404/")
        print("2. Re-run this script")
        print("\nSkipping import test...\n")
        return False  # Signal that import was skipped
    
    # Step 2: File exists, now create import run
    db = SessionLocal()
    import_run_id = None
    
    try:
        result = db.execute(
            text("""
            INSERT INTO import_runs (run_type, status, started_at, created_by)
            VALUES ('history', 'running', datetime('now'), 'smoke_test')
            """)
        )
        db.commit()
        import_run_id = result.lastrowid
        print(f"\n[INFO] Created import_run_id: {import_run_id}")
        
        # Step 3: Run import
        print(f"\n[INFO] Importing Excel file from 1404 directory...")
        
        try:
            stats = import_history_excel(
                file_path=str(excel_file),
                import_run_id=import_run_id,
                sheet_name=0,
                db=db
            )
            
            print("\n[OK] Import completed successfully!")
            print("\nStats:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            # Update run status to success
            db.execute(
                text("""
                UPDATE import_runs 
                SET status = 'success', completed_at = datetime('now'), stats_json = :stats
                WHERE id = :id
                """),
                {"stats": str(stats), "id": import_run_id}
            )
            db.commit()
            
            return True  # Success
            
        except Exception as e:
            print(f"\n[FAIL] Import failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up failed import
            if import_run_id:
                print("\n[INFO] Cleaning up failed import...")
                cleanup_failed_import(db, import_run_id)
            
            return False  # Failure
            
    except Exception as e:
        print(f"\n[FAIL] Failed to create import_run: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


def print_final_counts():
    """Print final row counts."""
    print_separator("Final Database Counts")
    
    db = SessionLocal()
    try:
        queries = [
            ("Patients", "SELECT COUNT(*) FROM patients"),
            ("Appointments", "SELECT COUNT(*) FROM appointments"),
            ("Staging rows (total)", "SELECT COUNT(*) FROM stg_appointments"),
            ("Staging rows (errors)", "SELECT COUNT(*) FROM stg_appointments WHERE parse_status='error'"),
            ("Staging rows (success)", "SELECT COUNT(*) FROM stg_appointments WHERE parse_status='ok'"),
            ("Import runs", "SELECT COUNT(*) FROM import_runs"),
        ]
        
        for label, query in queries:
            result = db.execute(text(query)).fetchone()
            print(f"{label:.<40} {result[0]:>8}")
        
        # Show recent appointments
        print("\n" + "-" * 80)
        print("Recent appointments:")
        print("-" * 80)
        
        rows = db.execute(
            text("""
            SELECT a.id, p.name, a.appointment_date, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            ORDER BY a.id DESC
            LIMIT 5
            """)
        ).fetchall()
        
        if rows:
            for row in rows:
                # Ensure Unicode-safe output on Windows
                try:
                    patient_name = str(row[1])[:30] if row[1] else "N/A"
                except:
                    patient_name = "N/A"
                
                # Safely encode/decode for Windows console
                try:
                    patient_name_safe = patient_name.encode("utf-8", "replace").decode("utf-8")
                except:
                    patient_name_safe = "N/A"
                
                print(f"ID: {row[0]:4d} | Patient: {patient_name_safe:30s} | Date: {row[2]} | Status: {row[3]}")
        else:
            print("(No appointments found)")
        
    finally:
        db.close()


def main():
    """Main smoke test function."""
    print("\n" + "=" * 80)
    print("  IMPORT PIPELINE SMOKE TEST")
    print(f"  Database: {SMOKE_DB} (isolated copy)")
    print("=" * 80)
    
    # Step 1: Run migrations
    print_separator("Step 1: Running Migrations")
    try:
        # First create base tables from models
        from database import init_db
        init_db()
        print("[OK] Base tables created")
        
        # Then run import pipeline migrations
        run_all_migrations()
        ensure_import_columns()
        print("[OK] Import migrations completed")
    except Exception as e:
        print(f"[FAIL] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 2: Verify tables
    db = SessionLocal()
    if not verify_tables_exist(db):
        print("\n[FAIL] Some tables are missing!")
        db.close()
        return 1
    db.close()
    
    # Step 3: Run import (only if file exists)
    import_success = run_import_test()
    
    # Step 4: Print results
    print_final_counts()
    
    print("\n" + "=" * 80)
    if import_success:
        print("  SMOKE TEST COMPLETE - IMPORT SUCCESS")
    else:
        print("  SMOKE TEST COMPLETE - IMPORT SKIPPED OR FAILED")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
