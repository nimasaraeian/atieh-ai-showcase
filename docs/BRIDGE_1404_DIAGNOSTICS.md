# 1404 Bridge Pipeline – Diagnostics & Fix Summary

## 1. Schema Inspection

### bridge_1404_payment_appointment
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| record_no | TEXT NOT NULL |
| appointment_patient_key | TEXT NOT NULL |
| payment_name_norm | TEXT |
| appointment_name | TEXT |
| appointment_phone | TEXT |
| appointment_date_key | TEXT |
| match_method | TEXT NOT NULL |
| confidence | REAL NOT NULL |
| payment_row_idx | INTEGER |
| appointment_row_idx | INTEGER |
| created_at | TEXT |
| **UNIQUE(record_no, appointment_patient_key)** | |

### bridge_1404_review
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| record_no | TEXT |
| payment_name_norm | TEXT |
| **review_reason** | TEXT NOT NULL |
| reason | TEXT |
| candidate_count | INTEGER |
| created_at | TEXT |

### patient_recordno_map_1404
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| record_no | TEXT NOT NULL UNIQUE |
| payment_name_norm | TEXT |
| appointment_name | TEXT |
| appointment_phone | TEXT |
| match_method | TEXT NOT NULL |
| confidence | REAL NOT NULL |
| created_at | TEXT |

## 2. Why `review_reason` Was Missing

The original schema used only `reason`. The script was updated to add `review_reason` as the primary column and keep `reason` for compatibility.

## 3. Root Causes of Tier A/C Being Zero (FIXED)

1. **Appointment phone column not found**: Appointment Excel headers had wrapping single quotes (e.g. `'تلفن'`). `_norm_header` did not strip them, so column matching failed and `col_phone` was `None` → no appointment phones loaded.
2. **Fix**: Added quote stripping in `_norm_header` (same as payments_importer).
3. **Persian/Arabic digits**: Phone numbers with ۰-۹ or ٠-٩ were not normalized to 0-9, so overlap checks failed.
4. **Fix**: Added `_normalize_digits()` and call it in `normalize_phones()` before extracting digits.

## 4. Post-Fix Results

| Metric | Before | After |
|--------|--------|-------|
| Tier A (date+name+phone) | 0 | 29,996 |
| Tier B (date+name unique) | 15,480 | 1,340 |
| Tier C (name+phone) | 0 | 1,079 |
| Total accepted | 15,480 | 32,415 |
| Distinct record_no | 7,515 | 11,602 |
| Distinct appointment_patient_key | N/A | 32,412 |

## 5. Deduplication

- Before: One bridge row per payment row → 15,480 rows for 7,515 distinct record_no (many duplicates).
- After: One row per `(record_no, appointment_patient_key)`.
- Multiple rows per record_no are kept when one patient has multiple appointments (different dates/phones).
