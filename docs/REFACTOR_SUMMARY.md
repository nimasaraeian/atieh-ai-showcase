# Repository Refactor Summary

This document summarizes the refactor performed to create a cleaner, recruiter-friendly repository structure.

## New Top-Level Structure

```
atieh/
├── app/           # Core application logic
├── routes/        # Route definitions
├── schemas/       # Pydantic schemas
├── tools/         # Build and tooling scripts
├── sql/           # SQL migrations and queries
├── static/        # Static web assets
├── public/        # Public assets
├── docs/          # Documentation (organized by category)
│   ├── setup/     # Setup and quickstart guides
│   ├── architecture/  # Technical architecture docs
│   ├── fixes/     # Bug fix and patch documentation
│   ├── runbooks/  # Operational runbooks
│   └── reports/   # Status and summary reports
├── scripts/       # Utility scripts
│   ├── checks/    # Check, inspect, qa scripts
│   ├── debug/     # Debug and underscore-prefix scripts
│   ├── migrations/ # Migration and conversion scripts
│   └── demos/     # Demo and sample data scripts
├── tests/
│   ├── unit/      # Pure logic tests
│   └── integration/ # API and flow tests
├── examples/      # Sample data and API examples
│   └── api/       # OpenAPI schema files
├── archive/       # Archived dev artifacts
│   ├── dev-notes/ # Old notes and scratch docs
│   └── debug-output/ # Generated logs and outputs
├── config/        # Configuration
├── data/          # Input/output data
├── exports/       # Export outputs
└── [root]         # Minimal: main.py, run.py, models, database, etc.
```

## Files Moved

### docs/setup/
- QUICKSTART.md, QUICKSTART_V2.md, QUICK_REFERENCE.md
- CRM_QUICKSTART.md, CRM_SETUP.md
- IMPORT_GUIDE.md, IMPORT_QUICK_START.md
- TEST_GUIDE.md, TEST_DATABASE_SETUP.md

### docs/architecture/
- ENGINE_README.md, ENGINE_SUMMARY.md, ENGINE_V2_DECISION_LOGIC.md
- SCHEDULER_README.md, SCORING_README.md
- TECHNICAL_ARCHITECTURE_REPORT.md, CRM_INTEGRATION_README.md

### docs/fixes/
- CHOKE_POINT_FIX.md, FINAL_CHOKE_POINT_SUMMARY.md, DATABASE_LOCK_FIX.md
- DOCTOR_MATCHING_IMPROVEMENTS.md
- IMPORT_FIX_COMPLETE.md, IMPORT_FIX_QUICKREF.md, IMPORT_PIPELINE_FIX_SUMMARY.md
- PREFERRED_DOCTOR_FIX_QUICKREF.md, PREFERRED_DOCTOR_FIX_SUMMARY.md
- PYTEST_IO_ERROR_FIX.md, PYTEST_QUICKFIX.md
- ROUTE_COLLISION_FIX.md, ROUTE_FIX_QUICKREF.md
- SQLITE_STABILITY_COMPLETE.md, SQLITE_STABILITY_FIX.md

### docs/reports/
- AI_CORE_HARDENING_SUMMARY.md, CHANGELOG_COMPLETE.md, IMPLEMENTATION_SUMMARY.md
- PRODUCTION_GRADE_SUMMARY.md, REPROCESS_COMPLETE.md, REPROCESS_QUICKREF.md
- STATUS.md, SUMMARY.md

### docs/runbooks/
- BRIDGE_PIPELINE_RUNBOOK.md, IMPORT_IMPLEMENTATION_COMPLETE.md, SMOKE_IMPORT_UPDATED.md

### archive/dev-notes/
- NOTES.md, test.md

### scripts/checks/
- check_*.py, inspect_*.py, qa_*.py, *_check.py (from root and scripts/)

### scripts/migrations/
- migrate_database.py, add_jalali_column.py, add_patients_data.py, convert_dates_jalali.py

### scripts/demos/
- demo_bugfixes.py, demo_scheduler.py, generate_sample_patients.py, add_sample_data.py

### scripts/debug/
- All _*.py (patch, fix, debug scripts from root and scripts/)

### tests/unit/
- test_loaders.py, test_normalize_doctor.py, test_doctor_name_normalize.py, test_doctor_normalize.py
- test_scoring.py, test_scoring_contract.py, test_confidence_range_and_variance.py
- test_tvs_components_in_range.py, test_score_components_sum.py, test_value_score_nonzero.py
- test_scheduling_no_overlap.py, test_logging_repr.py, test_persian_encoding_ok.py
- test_preferred_boost_trace_present.py, test_v1_unchanged.py, test_v2_has_trace.py

### tests/integration/
- test_api_recommend_slot.py, test_engine.py, test_recommend_slot_has_real_doctor.py
- test_routes_order.py, test_scheduler_preferred_doctor_id.py
- test_smoke_all_get_endpoints.py, test_preferred_doctor_robust.py

### examples/
- sample_patients.csv, sample_patients.json, sample_patients.txt

### examples/api/
- openapi.json, _openapi.json, _openapi_live.json

### archive/debug-output/
- pytest_collect.txt, pytest_run.txt, pytest_run2.txt
- query_*.txt, reprocess_*.txt, test_output.txt, test_redirect.txt
- response.json, api_response_correct.json, backfill_output.txt, verify_out.txt

## Import / Path Changes

1. **scripts/migrations/add_patients_data.py**
   - Reads from `examples/sample_patients.json` (repo-relative path)
   - Error message updated to reference `scripts/demos/generate_sample_patients.py`
   - Added `_repo_root` to sys.path for correct imports when run from any directory

2. **scripts/demos/generate_sample_patients.py**
   - Outputs now written to `examples/` directory (repo-relative)
   - Ensures `examples/` exists before writing

## .gitignore Updates

- Added: `.pytest_cache/`, `.coverage`, `*.log`
- Added: `*.db-wal`, `*.db-shm`
- Added: `.venv/`, `exports/generated/`, `archive/debug-output/`

## Files to Keep Private Before Going Public

- `.env` – environment variables and secrets
- `*.db`, `*.db-wal`, `*.db-shm` – database files (already in .gitignore)
- `data/inputs/` – proprietary Excel/data files
- `archive/debug-output/` – debug logs (in .gitignore)
- Any credentials or API keys in config

## Test Status

- **120 tests passed** after refactor
- 1 smoke test may fail if `data/reference/insurance_payment_priority.csv` is missing (pre-existing)
- Run tests: `pytest tests/ -v`
- Run from repo root; core modules (main.py, models, database, etc.) remain at root
