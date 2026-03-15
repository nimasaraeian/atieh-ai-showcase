# Identity Resolution Phase 1 – Runbook

## Environment

```bash
set ATIEH_DB_PATH=atieh_clinic_recovery81_test.db
```

Or export on Unix:

```bash
export ATIEH_DB_PATH=atieh_clinic_recovery81_test.db
```

## Prerequisites

- Database file exists at `ATIEH_DB_PATH` (or default `atieh_clinic_recovery81_test.db` in repo root).
- **Payments staging:** Run unified payments import first so `payments_unified_staging` is populated:
  ```bash
  python scripts/unified_payments_import.py
  ```
- Appointment Excel files under `data/inputs/history/<year>/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_<year>.xlsx` (and 1403: حضور پیدا کردند).

## Recommended full run order

From repo root:

```bash
# 1) Schema (identity resolution tables)
#    Applied automatically by each script; or run once:
sqlite3 %ATIEH_DB_PATH% < sql/identity_resolution/001_identity_resolution_schema.sql
sqlite3 %ATIEH_DB_PATH% < sql/identity_resolution/002_identity_resolution_indexes.sql

# 2) Appointment import (unified appointment staging)
python scripts/import_appointments_unified.py

# 3) Normalize identity fields (payments, appointments, patients)
python scripts/normalize_identity_fields.py

# 4) Candidate generation (payment↔patient, appointment↔patient, payment↔appointment)
python scripts/build_identity_candidate_matches.py

# 5) Scoring and tiers (A/B/C/D) and collision detection
python scripts/build_identity_match_scores.py

# 6) Stats and reports (markdown in docs/reports/)
python scripts/identity_resolution_stats.py
```

## Re-run only one stage

- **Appointments only:**  
  `python scripts/import_appointments_unified.py`  
  (Replaces rows in `appointments_unified_staging` per source file.)

- **Normalization only:**  
  `python scripts/normalize_identity_fields.py`  
  (Truncates and repopulates all three normalized tables.)

- **Candidates only:**  
  `python scripts/build_identity_candidate_matches.py`  
  (Deletes and rebuilds all candidate rows.)

- **Scoring only:**  
  `python scripts/build_identity_match_scores.py`  
  (Updates `score_raw`, `confidence_tier`, `match_status` on existing candidates.)

- **Reports only:**  
  `python scripts/identity_resolution_stats.py`  
  (Writes/overwrites markdown reports; does not change DB.)

## Output reports

| File | Content |
|------|--------|
| `docs/reports/appointments_unified_import_report.md` | K1 import stats, rows per year |
| `docs/reports/identity_normalization_report.md` | K2 normalization stats |
| `docs/reports/identity_candidate_match_report.md` | K3 candidate counts by pair and rule |
| `docs/reports/identity_match_scoring_report.md` | K4 tiers and match_status |
| `docs/reports/patient_identity_resolution_phase1_report.md` | K5 summary and phase 2 recommendation |

## Safety

- No updates to `patients` or `payments.patient_id`.
- All new data lives in staging, normalized, and candidate tables only.
