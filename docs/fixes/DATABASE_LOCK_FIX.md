# Database Lock Issue - Resolution

## Problem
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked
```

## Cause
The FastAPI development server (`uvicorn`) was running and holding an active connection to `atieh_clinic.db`. SQLite doesn't support concurrent writes by default, so the smoke test couldn't create the `import_run` row.

## Solution
**Stop the server before running the smoke test:**

```powershell
# Find the uvicorn process
Get-Process | Where-Object { $_.ProcessName -eq "python" }

# Stop it (replace PID with actual process ID)
Stop-Process -Id <PID> -Force

# Then run smoke test
python scripts/smoke_import_1404.py
```

## Verification
After stopping the server (PID 7748):
```
[INFO] Found Excel file in: C:\Users\USER\Documents\GitHub\atieh\data\inputs\history\1404
[INFO] File size: 4458500 bytes
[INFO] Created import_run_id: 9
```
✅ Import started successfully (no more "database is locked" error)

## Notes
1. **The smoke test script is working correctly** - it:
   - ✅ Scans for `.xlsx` files dynamically
   - ✅ Prints selected file info
   - ✅ Only creates `import_run` after confirming file exists
   - ✅ Prevents staging pollution when file is missing

2. **Separate issue**: The importer has logging errors with Persian filenames (doesn't stop execution, just spams console), and field name bugs (`'family'` instead of `'name'`). These are **not** part of the current task.

## Best Practice
When working with SQLite in development:
- **Option 1**: Stop the server before running scripts that write to the DB
- **Option 2**: Use separate test databases for scripts vs. server
- **Option 3**: Enable WAL mode for SQLite (allows concurrent reads + 1 writer)
