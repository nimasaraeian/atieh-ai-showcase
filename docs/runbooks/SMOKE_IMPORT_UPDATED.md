# Smoke Import Script - Updated

## Changes Made

### 1. Dynamic Excel File Discovery
- **Before**: Hardcoded filename `noubat_dehi_1404.xlsx`
- **After**: Scans `data/inputs/history/1404/` for first `.xlsx` file
- Prints file size and location (ASCII-safe for Windows console)
- Returns `None` if no file found

### 2. Prevents Staging Pollution
- **Before**: Created `import_run` row even if file didn't exist
- **After**: 
  - Checks file exists BEFORE creating `import_run`
  - Only creates import_run if file is found
  - No staging rows created if file missing

### 3. Failed Import Cleanup
- **New function**: `cleanup_failed_import(db, import_run_id)`
- Automatically called when import fails
- Actions:
  1. Deletes all `stg_appointments` rows for that `import_run_id`
  2. Marks `import_runs.status = 'failed'`
  3. Sets `import_runs.error` message
- Prevents accumulation of failed staging data

### 4. Windows Console Encoding Fix
- Replaced Unicode symbols with ASCII:
  - `✓` → `[OK]`
  - `✗` → `[FAIL]`
  - `⚠` → `[WARN]`
- Handles Persian filenames gracefully (shows file size instead of name if encoding fails)
- All output is ASCII-only

## Test Results

### Run Stats (with actual 1404 file)
```
[INFO] Found Excel file in: C:\Users\USER\Documents\GitHub\atieh\data\inputs\history\1404
[INFO] File size: 4458500 bytes
[INFO] Created import_run_id: 6
[INFO] Importing Excel file from 1404 directory...
2026-02-25 19:35:53,473 - Loaded 44724 rows from sheet '0'
2026-02-25 19:36:08,477 - Processed 7600/44724 rows...
```

### Known Issue (Separate from This Task)
The importer has a bug where it tries to use `family` and `mobile` fields that don't exist in the `Patient` model:
```
ERROR - Row X error: 'family' is an invalid keyword argument for Patient
ERROR - Row Y error: type object 'Patient' has no attribute 'mobile'
```

This causes ALL rows to fail parsing. **This is a bug in `app/importers/history_importer.py` that needs separate fixing.**

## Usage

### Run Smoke Test
```powershell
python scripts/smoke_import_1404.py
```

### Expected Behavior

**Scenario 1: No Excel file present**
```
[WARN] No .xlsx files found in: ...
[WARN] No Excel file found to import.

To test with actual data:
1. Place your Excel file (.xlsx) in: data/inputs/history/1404/
2. Re-run this script

Skipping import test...
```
- No `import_run` created
- No staging pollution
- Script continues to show table stats

**Scenario 2: Excel file present**
```
[INFO] Found Excel file in: ...
[INFO] File size: 4458500 bytes
[INFO] Created import_run_id: 6
[INFO] Importing Excel file from 1404 directory...
```
- Creates `import_run` row
- Attempts import
- If import fails → cleanup runs automatically

## Files Modified
- `scripts/smoke_import_1404.py`

## Next Steps (Not Part of This Task)
1. Fix `history_importer.py` to use correct Patient model fields (`name` instead of `family`, `phone` instead of `mobile`)
2. Fix column mapping heuristic to properly identify Persian column names
3. Add proper shamsi date parsing for 1404 format
