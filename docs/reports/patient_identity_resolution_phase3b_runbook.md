# Patient Identity Resolution Phase 3B – Runbook

## Goal

Expand from anchor patients (27,164) to **unrecovered** patients in the `patients` table by linking them to anchors. This is **patient expansion**, not row expansion.

## Environment

```powershell
$env:ATIEH_DB_PATH = "atieh_clinic_recovery81_test.db"
```

## Prerequisites

- Phase 1, 2, and 3 complete:
  - `identity_anchor_patients_phase3`, `identity_anchor_phone_phase3`, `identity_anchor_recordno_phase3`, `identity_anchor_name_phase3` populated
  - `safe_identity_matches_phase2` populated

## Run order

1. **Schema** (optional; scripts apply it)
   ```powershell
   sqlite3 $env:ATIEH_DB_PATH ".read sql/identity_resolution/006_phase3b_anchored_patient_expansion_schema.sql"
   sqlite3 $env:ATIEH_DB_PATH ".read sql/identity_resolution/007_phase3b_anchored_patient_expansion_indexes.sql"
   ```

2. **Unrecovered patients + candidates**
   ```powershell
   python scripts/build_patient_anchor_candidates_phase3b.py
   ```

3. **Score and promote**
   ```powershell
   python scripts/promote_patient_anchor_phase3b.py
   ```

4. **Stats and report**
   ```powershell
   python scripts/patient_identity_phase3b_stats.py
   ```

## Generated report

- `docs/reports/patient_identity_resolution_phase3b_report.md` – newly recovered, total recovered, coverage %, promotion by rule, ambiguity count, path toward 80k.

## Safety

- No updates to `patients` or `payments.patient_id`.
- Only reporting and phase3b tables are written.
