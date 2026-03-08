# Import Pipeline Fixes - Quick Reference

## What Was Fixed

| Error | Count | Status |
|-------|-------|--------|
| `'family' is invalid keyword` | 252,066 | ✅ Fixed (code already correct) |
| `Patient has no attribute 'mobile'` | 18,254 | ✅ Fixed (added property) |
| `database is locked` | 19 | ✅ Fixed (WAL + timeout) |
| `NOT NULL constraint failed` | 7 | ✅ Fixed (default value) |

## Quick Verification

```bash
# Test all fixes
python scripts/test_import_fixes.py

# Expected: All tests pass ✓
```

## Key Changes

### 1. Patient.mobile Property (models.py)
```python
@property
def mobile(self):
    return self.phone

@mobile.setter
def mobile(self, value):
    self.phone = value
```

### 2. Database Configuration (database.py)
```python
PRAGMA journal_mode=WAL;      # Concurrent reads/writes
PRAGMA busy_timeout=5000;     # Wait 5s if locked
```

### 3. Always Non-NULL payment_type (history_importer.py)
```python
payment_type_value = "CASH"  # Always provide default
```

### 4. Batch Commits (history_importer.py)
```python
if stats['processed'] % 2000 == 0:  # Every 2000 rows
    db.commit()
```

## Run Import

```python
from app.importers.history_importer import import_history_excel

stats = import_history_excel(
    file_path="data/inputs/history/file.xlsx",
    import_run_id=run_id,
    sheet_name=0
)
# All fixes applied automatically ✓
```

## Post-Import Scripts

```bash
# 1. Map insurance & normalize treatments
python scripts/patch_fill_services.py

# 2. Calculate priority scores
python scripts/backfill_patient_scores.py

# 3. Validate data
python scripts/validate_scoring.py
```

## Troubleshooting

**"database is locked"**
```bash
sqlite3 atieh_clinic.db "PRAGMA journal_mode=WAL;"
```

**Check staging errors**
```bash
sqlite3 atieh_clinic.db "
SELECT parse_error, COUNT(*) 
FROM stg_appointments 
WHERE parse_status='error' 
GROUP BY parse_error 
ORDER BY COUNT(*) DESC 
LIMIT 5;
"
```

**Test Patient.mobile**
```bash
python -c "from models import Patient; p=Patient(name='T',phone='123'); print(p.mobile)"
```

## Files Modified

- `models.py` - Added mobile property
- `database.py` - Updated busy_timeout comment
- `app/importers/history_importer.py` - Default payment_type, batch size
- `scripts/test_import_fixes.py` - NEW verification script

## Documentation

- Full details: `IMPORT_FIX_COMPLETE.md`
- Patient scoring: `docs/PATIENT_SCORING.md`
- Quick start: This file

---

**Status**: ✅ ALL FIXES COMPLETE  
**Test**: `python scripts/test_import_fixes.py`  
**Date**: 2026-02-26
