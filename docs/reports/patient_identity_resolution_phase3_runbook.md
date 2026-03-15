# Patient Identity Resolution Phase 3 – Runbook

## Environment

```powershell
$env:ATIEH_DB_PATH = "atieh_clinic_recovery81_test.db"
```

Or on Unix: `export ATIEH_DB_PATH=atieh_clinic_recovery81_test.db`

## Prerequisites

- Phase 1 and Phase 2 must be complete:
  - `payments_unified_staging`, `appointments_unified_staging` populated
  - `identity_normalized_*` and `patients_identity_normalized` populated
  - `identity_candidate_matches` and `build_identity_match_scores.py` run
  - `safe_identity_matches_phase2` populated (`scripts/populate_safe_identity_phase2.py`)

## Exact run order

1. **Schema**
   ```powershell
   sqlite3 $env:ATIEH_DB_PATH ".read sql/identity_resolution/004_phase3_graph_expansion_schema.sql"
   sqlite3 $env:ATIEH_DB_PATH ".read sql/identity_resolution/005_phase3_graph_expansion_indexes.sql"
   ```
   *(Or let the Python scripts apply schema automatically.)*

2. **Anchor profiles**
   ```powershell
   python scripts/build_identity_anchor_profiles_phase3.py
   ```

3. **Expansion candidates**
   ```powershell
   python scripts/build_identity_expansion_candidates_phase3.py
   ```

4. **Promotion (score + dominance + promote)**
   ```powershell
   python scripts/promote_identity_expansion_phase3.py
   ```

5. **Stats and reports**
   ```powershell
   python scripts/identity_phase3_stats.py
   ```

## Rerun instructions

- Each script is idempotent for its own tables (deletes then repopulates).
- To rerun only phase3: run steps 2–5 in order. Step 1 is optional if tables already exist.
- To rerun from candidates only: run steps 4 and 5.
- To regenerate reports only: run step 5.

## Scripts that can be run independently

| Script | Depends on | Can run alone? |
|--------|------------|----------------|
| `build_identity_anchor_profiles_phase3.py` | `safe_identity_matches_phase2`, normalized tables | Yes (after phase2) |
| `build_identity_expansion_candidates_phase3.py` | Anchor tables from step 2 | No – run after step 2 |
| `promote_identity_expansion_phase3.py` | `identity_expansion_candidates_phase3` | No – run after step 3 |
| `identity_phase3_stats.py` | Phase2 safe + phase3 promoted + anchor tables | Yes (after step 4) |

## Generated report files

| File | Content |
|------|--------|
| `docs/reports/patient_identity_resolution_phase3_graph_expansion_report.md` | K1–K7 metrics, L questions, coverage |
| `docs/reports/patient_identity_resolution_phase3_rule_diagnostics.md` | Payment↔appointment phone overlap diagnostic |

## Safety

- No updates to `patients` or `payments.patient_id`.
- All phase3 output is in phase3-specific tables only.
