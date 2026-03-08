# Import Pipeline Fix - Quick Reference

## Problem Solved

Fixed **301,741 parse errors** (88% error rate) caused by incorrect Patient schema usage:
- ❌ Old code tried to use `family` field (doesn't exist)
- ❌ Old code tried to use `mobile` field (doesn't exist)  
- ✅ Correct schema: name, phone, national_id, first_visit_date

## Solution

Created `scripts/reprocess_staging_errors.py` to correctly parse row_json with Persian keys.

## Quick Commands

```bash
# Reprocess all errors
python scripts/reprocess_staging_errors.py

# Reprocess specific import run
python scripts/reprocess_staging_errors.py --import-run-id 12

# Reprocess limited number (for testing)
python scripts/reprocess_staging_errors.py --limit 100
```

## Test Results

**Import Run 12**:
- Before: 44,724 errors (100%)
- After: 0 errors (0%)
- ✅ **100% success rate!**

## Correct Patient Schema

```python
Patient(
    name="نام کامل",              # Full name (no split)
    phone="09121234567",          # Phone number
    national_id="1234567890",     # Optional
    first_visit_date=datetime     # From appointment date
)
```

## Persian Key Mapping

| row_json Key | Database Field |
|--------------|----------------|
| `'نام بيمار(تشكيل پرونده شده)'` | patients.name |
| `'تلفن'` | patients.phone |
| `'تاريخ نوبت'` | appointments.appointment_date |
| `'ساعت نوبت'` | appointments.appointment_date |
| `'نام پزشک'` | appointments.raw_text_doctor |
| `'توضيحات'` | appointments.raw_text_service |
| `'سازمان بيمه گر'` | appointments.raw_text_insurance |

## Check Status

```bash
# View parse status counts
sqlite3 atieh_clinic.db "
SELECT parse_status, COUNT(*) 
FROM stg_appointments 
GROUP BY parse_status;
"

# Check specific import run
sqlite3 atieh_clinic.db "
SELECT parse_status, COUNT(*) 
FROM stg_appointments 
WHERE import_run_id=12 
GROUP BY parse_status;
"
```

## Files

- **Script**: `scripts/reprocess_staging_errors.py`
- **Full Docs**: `REPROCESS_COMPLETE.md`  
- **Import Fix**: `IMPORT_FIX_COMPLETE.md`
- **Quick Ref**: This file

## Next Steps

After reprocessing:
1. `python scripts/patch_fill_services.py` - Map insurance/treatments
2. `python scripts/backfill_patient_scores.py` - Calculate priority scores
3. `python scripts/validate_scoring.py` - Validate data

---

**Status**: ✅ Complete  
**Date**: 2026-02-26  
**Success Rate**: 100%
