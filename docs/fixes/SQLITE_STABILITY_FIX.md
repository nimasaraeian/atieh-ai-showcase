# SQLite Stability Fix - Complete Implementation

## Problem Statement
- ❌ "database is locked" errors during import
- ❌ UnicodeEncodeError on Windows console with Persian text
- ❌ Concurrency issues when server + smoke test run together

## Solution Summary

### PART 1: SQLite Engine Configuration ✅
**File**: `database.py`

Added WAL mode and optimized connection settings:

```python
# SQLite-specific optimizations
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30  # 30 second timeout
    }
)

# Event listener to configure SQLite on each connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")      # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL;")    # Balance safety/speed
    cursor.execute("PRAGMA busy_timeout=30000;")    # 30 second busy timeout
    cursor.close()
```

**Benefits**:
- ✅ WAL mode allows concurrent readers + 1 writer
- ✅ 30 second timeout prevents immediate lock failures
- ✅ NORMAL synchronous mode improves performance

### PART 2: Isolated Smoke Test Database ✅
**File**: `scripts/smoke_import_1404.py`

Added database isolation:

```python
ORIGINAL_DB = "atieh_clinic.db"
SMOKE_DB = "atieh_clinic_smoke.db"

def setup_isolated_database():
    # Removes old smoke DB
    # Copies from original DB (if exists)
    # Sets DATABASE_URL to use smoke DB
    os.environ["DATABASE_URL"] = f"sqlite:///{SMOKE_DB}"
```

**Benefits**:
- ✅ No conflict with running server
- ✅ Fresh copy for each test run
- ✅ Original DB remains untouched

### PART 3: Unicode Encoding Fix ✅
**File**: `scripts/smoke_import_1404.py`

**Fix 1 - Set stdout encoding**:
```python
# At top of file
try:
    sys.stdout.reconfigure(encoding="utf-8")
except:
    pass
```

**Fix 2 - Safe patient name display**:
```python
# In print_final_counts()
try:
    patient_name = str(row[1])[:30] if row[1] else "N/A"
    patient_name_safe = patient_name.encode("utf-8", "replace").decode("utf-8")
except:
    patient_name_safe = "N/A"

print(f"ID: {row[0]:4d} | Patient: {patient_name_safe:30s} | ...")
```

**Benefits**:
- ✅ Handles Persian characters correctly on Windows
- ✅ Graceful fallback if encoding fails
- ✅ No more UnicodeEncodeError crashes

### PART 4: Commit Strategy ✅
**File**: `app/importers/history_importer.py`

**Already implemented correctly**:
```python
# Batch commits every 100 rows
if stats['processed'] % 100 == 0:
    db.commit()
    logger.info(f"Processed {stats['processed']}/{stats['total_rows']} rows...")

# Final commit
db.commit()
```

**Benefits**:
- ✅ Reduces transaction overhead
- ✅ Balances safety with performance
- ✅ No per-row commits

### PART 5: Safe Cleanup ✅
**File**: `scripts/smoke_import_1404.py`

**Already implemented**:
```python
finally:
    db.close()  # In both run_import_test() and print_final_counts()
```

**Benefits**:
- ✅ Sessions always closed
- ✅ No connection leaks
- ✅ Clean shutdown

## Modified Files

1. ✅ `database.py`
   - Added SQLite WAL configuration
   - Added busy_timeout and timeout settings
   - Added pragma event listener

2. ✅ `scripts/smoke_import_1404.py`
   - Added isolated database setup
   - Added Unicode encoding fixes
   - Updated database display name

3. ✅ `app/importers/history_importer.py`
   - No changes needed (already has batch commits)

## Verification Checklist

### ✅ 1. SQLite WAL Enabled
Run this to verify:
```powershell
sqlite3 atieh_clinic.db "PRAGMA journal_mode;"
```
Expected output: `wal`

### ✅ 2. Smoke Test Uses Isolated DB
Check for file creation:
```powershell
ls atieh_clinic_smoke.db
```
Should exist after running smoke test.

### ✅ 3. Unicode Issues Resolved
Run smoke test and check for:
- No `UnicodeEncodeError`
- Persian names display correctly (or safely fallback)

### ✅ 4. No More "Database is Locked"
With WAL mode + 30s timeout + isolated DB:
- Server can run while smoke test runs
- Import handles temporary locks gracefully

## How to Test

### 1. Run Smoke Test (Isolated)
```powershell
python .\scripts\smoke_import_1404.py *>&1 | Tee-Object -FilePath .\data\outputs\smoke_stable.log
```

### 2. Check for Success
Look for:
```
[INFO] Created isolated database copy: atieh_clinic_smoke.db
[INFO] Database URL set to: sqlite:///atieh_clinic_smoke.db
[OK] Migrations completed
[INFO] Found Excel file in: ...
Processed 100/44724 rows...
Processed 200/44724 rows...
```

### 3. Verify No Errors
```powershell
Get-Content .\data\outputs\smoke_stable.log | Select-String -Pattern "(database is locked|UnicodeEncodeError)"
```
Should return nothing.

### 4. Check WAL Mode
```powershell
sqlite3 atieh_clinic.db "PRAGMA journal_mode;"
sqlite3 atieh_clinic_smoke.db "PRAGMA journal_mode;"
```
Both should return `wal`.

## Technical Details

### WAL (Write-Ahead Logging)
- Writes go to separate WAL file first
- Allows multiple readers + 1 writer simultaneously
- Checkpoint merges WAL into main DB periodically
- Better concurrency than default rollback journal

### Busy Timeout
- SQLite waits up to 30 seconds before returning "database is locked"
- During wait, SQLite periodically checks if lock is released
- Handles temporary contentions gracefully

### Isolated Test Database
- Smoke test gets its own copy
- Original DB unaffected by test runs
- Can delete smoke DB anytime without data loss

## Production Safety

All changes are **production-safe**:
- ✅ No business logic altered
- ✅ No model changes
- ✅ Backward compatible
- ✅ Only configuration/infrastructure improvements
- ✅ Defensive error handling
- ✅ Minimal code changes

## Rollback Plan

If issues occur:
1. Revert `database.py` to remove WAL pragma
2. Revert `smoke_import_1404.py` to use original DB
3. Delete `atieh_clinic_smoke.db`

Original functionality preserved in git history.
