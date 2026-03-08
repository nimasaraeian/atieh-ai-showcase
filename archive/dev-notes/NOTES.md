# Project Structure Notes - AI Core Hardening Phase

## Date: 2026-02-05

## Key Files Located:

### Entry Points:
- **FastAPI Main**: `main.py` (was `app.py`, renamed to avoid conflict with `app/` package) ✅
- **Run Script**: `run.py` ✅
- **Important**: File renamed from `app.py` to `main.py` due to naming conflict with `app/` directory

### AI Core Modules:
- **AI Brain**: `ai_brain.py` (188+ lines) ✅
- **Scoring Algorithm**: `scoring_algorithm.py` ✅
- **Appointment Scheduler**: `appointment_scheduler.py` ✅
- **Treatment Duration**: `treatment_duration.py` ✅

### CRM Integration:
- **CRM Integration Module**: `crm_integration.py` (312 lines) ✅
- **CRM Adapter**: `app/integrations/crm/adapter.py` ✅
- **CRM Client Interface**: `app/integrations/crm/client.py` ✅
- **Mock CRM**: `app/integrations/crm/mock.py` ✅

### Database Models:
- **Main Models**: `models.py` (115 lines) ✅
  - Patient, Appointment, ClinicSchedule, PaymentType, TreatmentType

### Schemas:
- **Existing Schemas**: `schemas/` folder ✅
  - `appointment_schemas.py`
  - `patient_schemas.py`
  - `__init__.py`
- **Engine Schemas**: `app/schemas/scheduling.py` ✅
  - PatientContext, SchedulingRequest, CaseContext

### Engine:
- **Engine Folder**: `app/engine/` ✅
  - `recommender.py` - موتور پیشنهادات
  - `scheduler.py` - سیستم زمان‌بندی
  - `scoring.py` - امتیازدهی
  - `slot_builder.py` - ساختن بازه‌های زمانی
  - `time_blocks.py` - مدیریت بلوک‌های زمانی
  - `run_engine.py` - Entry points

### Utilities:
- **Persian Normalization**: `app/utils/fa_normalize.py` ✅
- **Name Normalization**: `app/utils/name_normalize.py` ✅

### Data:
- **Input Data**: `data/inputs/` ✅
- **Output Data**: `data/outputs/` ✅

### Tests:
- **Test Folder**: `tests/` ✅
  - `test_scoring.py`
  - `test_loaders.py`
  - `test_engine.py`

## Current Architecture:

```
atieh/
├── app.py (FastAPI entry point)
├── run.py (server startup)
├── ai_brain.py (AI scoring)
├── scoring_algorithm.py (rule-based scoring)
├── appointment_scheduler.py (scheduling logic)
├── crm_integration.py (CRM module - current)
├── models.py (SQLAlchemy models)
├── database.py (DB config)
├── app/
│   ├── engine/ (scheduling engine)
│   ├── integrations/crm/ (CRM adapters)
│   ├── schemas/ (Pydantic schemas)
│   ├── loaders/ (Excel data loaders)
│   └── utils/ (helpers)
├── schemas/ (API schemas)
├── routes/ (API routes)
├── static/ (frontend)
├── data/ (input/output data)
└── tests/ (test suite)
```

## Task Plan:

### Phase 1: Contracts & Config ✅ READY TO START
1. Create `app/schemas/ai_contract.py` - Stable AI output schema
2. Create `config/weights.yaml` - Config-driven weights
3. Create `app/config.py` - Config loader

### Phase 2: Mock Data ✅ READY TO START
4. Create `data/mock/` folder
5. Create `scripts/generate_mock_crm_data.py` - Mock data generator
6. Generate realistic datasets (200+ patients, 1000+ appointments)

### Phase 3: CRM Adapter Hardening ✅ READY TO START
7. Update `app/integrations/crm/interface.py` - Abstract interface
8. Update `app/integrations/crm/mock_client.py` - Read from JSON
9. Update `app/integrations/crm/live_client.py` - Skeleton only
10. Create `app/integrations/crm/mapper.py` - CRM → Canonical mapping

### Phase 4: Canonical Models ✅ READY TO START
11. Create `app/schemas/canonical.py` - Internal models

### Phase 5: Engine Update ✅ READY TO START
12. Update engine to use canonical models
13. Create deterministic `recommend_slots()` function

### Phase 6: API Endpoints ✅ READY TO START
14. Add `/health` endpoint
15. Add `/ai/score-patient` endpoint
16. Add `/ai/recommend-slot` endpoint
17. Add CRM_MODE dependency injection

### Phase 7: Tests ✅ READY TO START
18. Create `tests/test_scoring_contract.py`
19. Create `tests/test_scheduling_no_overlap.py`
20. Create `tests/test_api_recommend_slot.py`

### Phase 8: Easy Run ✅ READY TO START
21. Create `scripts/run_local.sh` / `scripts/run_local.ps1`
22. Create Makefile (optional)
23. Update QUICKSTART.md

## Dependencies to Add:
- pyyaml (for config loading)
- Faker (for realistic mock data generation - optional)

## Environment Variables Used:
- CRM_MODE=mock|live (default: mock)
- CRM_BASE_URL
- CRM_API_KEY
- CRM_AUTH_TYPE
- CRM_TIMEOUT
- CRM_ENABLED

## Notes:
- Project already has good structure
- CRM integration exists but needs hardening
- Mock CRM exists but needs realistic data
- Engine exists but needs canonical models
- Tests exist but need end-to-end coverage
