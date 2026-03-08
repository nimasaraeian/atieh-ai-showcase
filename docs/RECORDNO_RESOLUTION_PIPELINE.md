# Record No Resolution Pipeline

Pipeline to link **patients** (scheduling system) to **financial data** (payments) via **record_no** (clinic file/chart number).

## Summary

- **Financial data** (`payments_clean`): `patient_name_raw` is always `"Name(record_no)"`; `record_no` is the clinic file number.
- **Scheduling/Appointment Excel files**: Do **not** contain a patient file number column; patient name is plain (e.g. "عليزاده سعيد") with no `(record_no)` suffix. The column "شماره نوبت" is the **appointment slot number**, not the patient file number.
- The **bridge** is therefore populated from **payments_clean** (one row per distinct `record_no` with name/phone), then matched to **patients** by normalized name and phone to build **patient_recordno_map**.

## Files Created / Modified

### New scripts (tools/)

| File | Purpose |
|------|--------|
| `tools/discover_recordno_in_appointments.py` | Phase 1: Scan appointment Excel files; report columns and whether record_no exists (or is parsable from name). |
| `tools/build_appointment_recordno_bridge.py` | Phase 2: Build `appointment_recordno_bridge` from (1) appointment files if they had record_no, (2) **payments_clean** (distinct record_no + name/phone). |
| `tools/build_patient_recordno_map.py` | Phase 3: Match bridge to `patients` (name+phone, then name-only when unique); fill `patient_recordno_map` and `patient_recordno_map_review`. |
| `tools/run_recordno_resolution_pipeline.py` | Orchestrator: run discover → bridge → map → apply view migration → print validation. |

### New migrations (app/db/migrations/)

| File | Purpose |
|------|--------|
| `013_appointment_recordno_bridge.sql` | Table `appointment_recordno_bridge` + indexes. |
| `014_patient_recordno_map.sql` | Tables `patient_recordno_map`, `patient_recordno_map_review` + indexes. |
| `015_v_patients_financial_resolved.sql` | View `v_patients_financial_resolved` (patients + record_no + financial summary). |

## Commands (PowerShell, run from repo root)

```powershell
# Full pipeline (discover + bridge + map + validate)
python tools/run_recordno_resolution_pipeline.py

# Skip discovery (only bridge + map + validate)
python tools/run_recordno_resolution_pipeline.py --skip-discover

# Only Phase 1 discovery report
python tools/run_recordno_resolution_pipeline.py --discover-only

# Only validation (after pipeline already run)
python tools/run_recordno_resolution_pipeline.py --validate-only
```

Manual step order if you run scripts individually:

```powershell
python tools/build_appointment_recordno_bridge.py
python tools/build_patient_recordno_map.py
python tools/run_recordno_resolution_pipeline.py --validate-only
```

Ensure before running:

- `payments_clean` is populated (run `tools/build_payments_clean.py` and optionally `scripts/ingest_payments.py` if needed).
- `patient_financial_summary` is populated (run `tools/build_patient_financial_summary.py`).
- Migrations 013, 014, 015 are applied (or run `python -c "from app.db.run_migrations import run_all_migrations; run_all_migrations()"`).

## Validation Queries (Phase 5)

After the pipeline runs, the orchestrator prints:

1. Total patients  
2. Total distinct record_no in financial data (payments_clean)  
3. Total distinct record_no in appointment bridge  
4. Total patient_id mapped to record_no (patient_recordno_map)  
5. Total patients with financial linkage **before** (payments_clean.patient_id only)  
6. Total patients with financial linkage **after** (payments_clean ∪ patient_recordno_map with financial)  
7. Coverage increase (count and %)  
8. Top 20 high-value matched patients (v_patients_financial_resolved)  
9. Top 20 unresolved financial record_no (high value, not in map)  
10. Top 20 ambiguous (patient_recordno_map_review)  

Ad-hoc SQL (SQLite):

```sql
-- Patients with resolved financial (record_no + summary)
SELECT * FROM v_patients_financial_resolved WHERE financial_value > 0 LIMIT 20;

-- Count linked after pipeline
SELECT COUNT(DISTINCT patient_id) FROM payments_clean WHERE patient_id IS NOT NULL
UNION ALL
SELECT COUNT(DISTINCT prm.patient_id)
FROM patient_recordno_map prm
JOIN patient_financial_summary pfs ON pfs.record_no = prm.record_no;
```

## Design Notes

- **patients** table is not modified; `patient_recordno_map` is the official bridge from patient_id to record_no.
- Matching priority: (A) exact normalized name + exact normalized phone, (B/C) exact normalized name only when that name is unique in patients. Ambiguous cases go to `patient_recordno_map_review`.
- Bridge is seeded from **payments_clean** because appointment Excel files do not contain patient file numbers; this gives maximum linkage of financial record_no to patients by name/phone.
