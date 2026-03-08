# Import Pipeline - Complete Reference

## Database Path
```
atieh_clinic.db (SQLite in project root)
```

## Running the System

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Run Smoke Test (Migrations + Import)
```powershell
python scripts/smoke_import_1404.py
```

This will:
- Run all migrations
- Create tables (import_runs, stg_appointments, etc.)
- Attempt to import 1404 file if it exists
- Print database counts

### 3. Start API Server
```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Migrations run automatically on startup.

## API Endpoints

All endpoints are available at: http://127.0.0.1:8000/docs

### GET /api/import/ping
Health check.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/ping"
```

Expected: `{"status":"ok","message":"Import API is running"}`

### POST /api/import/history
Import historical Excel files.

```powershell
$body = @{
    files = @(
        @{
            path = "data/inputs/history/1404/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx"
            year = 1404
            sheet = 0
        }
    )
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/import/history" `
    -Method POST `
    -Body $body `
    -ContentType "application/json; charset=utf-8"

$response | ConvertTo-Json
```

### GET /api/import/runs
List recent import runs.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/runs"
```

### GET /api/import/runs/{id}
Get details of specific import run.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/runs/1"
```

### GET /api/import/runs/{id}/errors
Get error rows for specific import run.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/runs/1/errors"
```

### GET /api/import/stats
Get overall import statistics.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/stats"
```

## Code Examples

### Migration Function (Fixed)
```python
# app/db/run_migrations.py
def run_migration(migration_file: Path):
    """Use raw SQLite connection for executescript."""
    db_path = get_db_path()  # Returns: atieh_clinic.db
    logger.info(f"Target database: {db_path}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    with engine.begin() as conn:
        raw_conn = conn.connection.connection  # Get sqlite3 connection
        raw_conn.executescript(sql_content)
```

### SQL Execution with text() (Fixed)
```python
# Example 1: INSERT with named parameters
db.execute(
    text("""
    INSERT INTO stg_appointments 
    (import_run_id, file_name, row_number, row_json, loaded_at)
    VALUES (:import_run_id, :file_name, :row_number, :row_json, :loaded_at)
    """),
    {
        "import_run_id": 123,
        "file_name": "file.xlsx",
        "row_number": 5,
        "row_json": "{}",
        "loaded_at": datetime.now().isoformat()
    }
)

# Example 2: SELECT with named parameter
result = db.execute(
    text("SELECT id FROM appointments WHERE source_row_hash = :hash"),
    {"hash": hash_value}
).fetchone()

# Example 3: UPDATE with named parameters
db.execute(
    text("UPDATE stg_appointments SET parse_status = :status WHERE id = :id"),
    {"status": "ok", "id": 123}
)
```

## Database Schema

### import_runs
```sql
CREATE TABLE import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,  -- 'history', 'reference', 'manual'
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    stats_json TEXT,
    error_message TEXT,
    created_by TEXT DEFAULT 'system'
);
```

### stg_appointments
```sql
CREATE TABLE stg_appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    sheet_name TEXT,
    row_number INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    parse_status TEXT NOT NULL DEFAULT 'pending',
    parse_error TEXT,
    patient_id INTEGER,
    appointment_id INTEGER,
    FOREIGN KEY (import_run_id) REFERENCES import_runs(id)
);
```

### appointments (extended columns)
```sql
-- Added columns:
ALTER TABLE appointments ADD COLUMN source_row_hash TEXT;
ALTER TABLE appointments ADD COLUMN raw_text_doctor TEXT;
ALTER TABLE appointments ADD COLUMN raw_text_service TEXT;
ALTER TABLE appointments ADD COLUMN raw_text_insurance TEXT;
ALTER TABLE appointments ADD COLUMN import_run_id INTEGER;

CREATE UNIQUE INDEX idx_appointments_source_hash 
    ON appointments(source_row_hash) 
    WHERE source_row_hash IS NOT NULL;
```

## Troubleshooting

### Check if migrations ran
```powershell
sqlite3 atieh_clinic.db ".tables"
```
Should show: `import_runs`, `stg_appointments`, `stg_reference_rows`

### Verify row counts
```powershell
sqlite3 atieh_clinic.db "SELECT COUNT(*) FROM import_runs"
sqlite3 atieh_clinic.db "SELECT COUNT(*) FROM stg_appointments"
sqlite3 atieh_clinic.db "SELECT COUNT(*) FROM appointments"
```

### Check API endpoints
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/openapi.json" | 
    ConvertTo-Json -Depth 10 | 
    Select-String "api/import"
```

Should show all 6 endpoints:
- /api/import/ping
- /api/import/history
- /api/import/runs
- /api/import/runs/{run_id}
- /api/import/runs/{run_id}/errors
- /api/import/stats

## File Placement

Place Excel files here:
```
data/
  inputs/
    history/
      1404/
        نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx
```

Pathlib handles Persian filenames correctly on Windows.

## Testing Workflow

1. **Run smoke test:**
   ```powershell
   python scripts/smoke_import_1404.py
   ```

2. **Start server:**
   ```powershell
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Test API:**
   ```powershell
   # Ping
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/ping"
   
   # Import
   $body = @{files=@(@{path="data/inputs/history/1404/file.xlsx";year=1404;sheet=0})} | ConvertTo-Json -Depth 10
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/history" -Method POST -Body $body -ContentType "application/json; charset=utf-8"
   
   # Check results
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/stats"
   ```

## Success Criteria

✅ Migrations create all tables  
✅ `/api/import/ping` returns 200  
✅ `/api/import/history` POST accepts file path  
✅ Database populates with patients/appointments  
✅ Deduplication works (same file imported twice = no duplicates)  
✅ Persian filenames handled correctly  
✅ Jalali dates converted to Gregorian  
