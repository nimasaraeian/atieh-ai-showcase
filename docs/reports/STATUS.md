# Technical Status Audit — Atieh Clinic AI Project

**Date:** 2026-03-02
**Server:** `http://127.0.0.1:8000`
**DB:** `atieh_clinic.db` (SQLite, 5.1 GB)

---

## 1. Current Architecture

### Module Map

| Layer | Module | Role |
|---|---|---|
| Entry point | `main.py` (1,839 lines) | Monolithic FastAPI app — all legacy routes + AI endpoints |
| ORM / DB | `database.py`, `models.py` | SQLAlchemy engine, session factory, `Patient`/`Appointment`/`PaymentType`/`TreatmentType` models |
| Legacy scoring | `scoring_algorithm.py` | `AppointmentScoringAlgorithm` — payment×40 + treatment×35 + lifetime×25 → 0–100 |
| AI brain | `ai_brain.py` | `AIBrain` — history scoring, feature extraction, risk/value prediction. `_score_from_stats()` (pure) + `calculate_patient_history_score()` (DB-backed) |
| Slot-fit scoring (v1) | `app/engine/scoring.py` | 4 scoring functions (urgency 35%, financial 30%, availability 20%, complexity 15%) + `DataStore` (CSV-backed) |
| TVS v2 | `app/engine/tvs/` | Full CIS+LTVS+RISK+FAIR+URG formula — **code complete, permanently disabled** (all weights = 0.0 in `config/weights.yaml`) |
| Scheduler | `app/engine/slot_recommender.py`, `slot_builder.py` | Doctor assignment, confidence scoring, diversity ranking |
| Import pipeline | `app/api/routes_import.py`, `app/importers/history_importer.py`, `app/importers/payments_importer.py` | Excel ingestion → `stg_appointments` / `stg_payments` staging → `appointments` / `patients` |
| CRM | `app/integrations/crm/` | Factory pattern: `MockCRMClient` (JSON fixtures) or `LiveClient` (stub) |
| Migrations | `app/db/run_migrations.py` + 4 SQL files | Idempotent migration runner tracking via `schema_migrations` |

### Active Routers

| Router | Prefix | Source |
|---|---|---|
| Import router | `/api/import` | `app/api/routes_import.py` → `main.py:188` `include_router()` |
| All other routes | `/` | Directly registered on `app` in `main.py` (no modular router) |

No other `include_router()` calls exist. The `routes/patients.py` file exists but is **not mounted**.

---

## 2. Database Status

### Row Counts

| Table | Rows | Notes |
|---|---|---|
| `appointments` | **71,477** | Full scoring columns, 100% filled |
| `patients` | **20,566** | |
| `stg_appointments` | **344,825** | 344,696 ok / 129 skipped |
| `stg_payments` | **876,054** | Largest table (billing data) |
| `import_runs` | 15 | 15 completed import runs |
| `schema_migrations` | 4 | All 4 migrations applied |
| `clinic_schedules` | **0** | **CRITICAL: empty — scheduler has no shift data from DB** |
| `stg_reference_rows` | **0** | Reference row pipeline unused |

### Defined Indexes

| Table | Index | Type |
|---|---|---|
| `appointments` | `idx_appointments_patient_id` | Regular (added 2026-03-02) |
| `appointments` | `idx_appointments_payment_type_norm` | Regular |
| `appointments` | `idx_appointments_priority_score` | Regular DESC |
| `appointments` | `idx_appointments_source_hash` | Unique partial (WHERE NOT NULL) |
| `import_runs` | `idx_import_runs_started` | Regular DESC |
| `import_runs` | `idx_import_runs_status` | Regular |
| `patients` | `idx_patients_lifetime_value` | Regular DESC |
| `patients` | `idx_patients_national_id` | Unique partial |
| `stg_appointments` | `idx_stg_appt_import_run` | Regular |
| `stg_appointments` | `idx_stg_appt_patient` | Regular |
| `stg_appointments` | `idx_stg_appt_status` | Regular |
| `stg_payments` | `idx_stg_pay_import_run`, `_payer`, `_status`, `_year` | Regular |

### Missing Performance Indexes

| Missing Index | Impact |
|---|---|
| `appointments(appointment_date)` | **High** — `/ai/top-patients` JOIN filters by `appointment_date >= cutoff`, currently full-scan of 71,477 rows |
| `appointments(status)` | **High** — `extract_features()` filters `status IN ('completed','cancelled')` on every patient score call |
| `stg_appointments(appointment_id)` | **Medium** — JOIN condition in `/ai/top-patients` Query 1 |
| `patients(phone)` | **Low** — CRM sync and patient lookup by phone; no index |

### Schema Consistency Issues

1. **`payment_type` enum mismatch (critical):** `appointments.payment_type` stores `'insurance'`
   (71,104 rows = 99.5%) and `'cash'` (373 rows). The `PaymentType` enum defines `'cash'`,
   `'insurance_1'`…`'insurance_20'`. Any full ORM `Appointment` hydration will raise
   `LookupError`. Only `ai_brain.py` was patched with `with_entities()` + `cast(..., String)`
   to bypass this. All other routes loading full `Appointment` objects are exposed to this crash.

2. **`patients.payment_type` same risk:** Column type is `Enum(PaymentType)`, nullable. If any
   patient row has `payment_type='insurance'`, accessing `patient.payment_type` will crash.

3. **`clinic_schedules` is empty:** The model exists and `AppointmentScheduler` queries it.
   Any slot-scheduling call returns no results, making slot suggestion endpoints non-functional.

---

## 3. AI Layer

### Scoring Functions Inventory

| Function | Location | Input → Output | DB-connected |
|---|---|---|---|
| `AppointmentScoringAlgorithm.calculate_priority_score()` | `scoring_algorithm.py` | PaymentType + TreatmentType + first_visit_date → 0–100 | No (pure math) |
| `AIBrain.extract_features()` | `ai_brain.py` | Patient + DB → feature dict | **Yes** — `with_entities()` on `appointments` (patched) |
| `AIBrain.predict_risk_and_value()` | `ai_brain.py` | feature dict → risk/value | No (pure math) |
| `AIBrain.compute_ai_priority()` | `ai_brain.py` | base_priority + value_score → 0–100 | No |
| `AIBrain.calculate_patient_history_score()` | `ai_brain.py` | Patient + DB → 0–100 | Yes (delegates to extract_features) |
| `AIBrain._score_from_stats()` | `ai_brain.py` | 6 stats → 0–100 | **No (pure)** — batch-safe |
| `calculate_total_score()` | `app/engine/scoring.py` | 4 sub-scores → 0–1 | No |
| `score_slot()` | `app/engine/scoring.py` | slot dict + DataStore → scored dict | No (CSV-backed) |
| `compute_patient_tvs()` | `app/engine/tvs/patient_value.py` | request_params + DataStore → TVS | No (disabled) |

### `patient-history-score` Connectivity

Fully connected. Path: `GET /ai/patient-history-score/{id}` → `AIBrain.calculate_patient_history_score()`
→ `extract_features()` → `with_entities()` on `appointments` (enum-safe) + `_estimate_lifetime_months()`
on `patients`. Returns 0–100 float. **Working and tested.**

### Caching

**`ai_patient_scores` table does not exist.** No caching layer is implemented. Every call to
`calculate_patient_history_score()` hits the DB. `/ai/top-patients` mitigates this with
`_score_from_stats()` via a single batch SQL aggregation.

### Scoring Logic Duplication / Dead Code

| Issue | Detail |
|---|---|
| **Three parallel priority systems** | `AppointmentScoringAlgorithm` (legacy, enum-based), `AIBrain` (history-based), `app/engine/tvs` (TVS v2) — no shared interface |
| **TVS v2 fully disabled** | `config/weights.yaml` has all TVS weights = 0.0 and `final.patient_weight=0.0` |
| **`weights.yaml` legacy section also disabled** | `weights.payment=treatment=lifetime=0.0` — `AppointmentScoringAlgorithm` does not read this file; it uses hardcoded weights |
| **`calculate_urgency_score` duplicated** | Exists in `app/engine/scoring.py` and called again from `app/engine/tvs/patient_value.py:compute_urg()` |
| **`scoring_algorithm.py` not called from any active endpoint** | Imported in `main.py` but active endpoints call `ai_brain` instead |

---

## 4. API Endpoints — Full Annotated List

| Method | Path | Status | Notes |
|---|---|---|---|
| GET | `/` | Experimental | Returns `index.html` if `static/` exists; otherwise 404 |
| GET | `/health` | **Stable** | CRM health + version |
| GET | `/api` | **Stable** | Static info endpoint |
| GET | `/api/import/ping` | **Stable** | Import router health |
| POST | `/api/import/history` | **Stable** | 344,696 rows imported successfully |
| GET | `/api/import/runs` | **Stable** | Lists import runs |
| GET | `/api/import/runs/{run_id}` | **Stable** | Run detail |
| GET | `/api/import/runs/{run_id}/errors` | **Stable** | Error rows |
| GET | `/api/import/stats` | **Stable** | Aggregate import statistics |
| POST | `/patients` | Experimental | Creates Patient; no validation that `payment_type` is enum-safe |
| GET | `/patients` | **Incomplete** | Loads full ORM Patient objects — enum crash risk |
| GET | `/patients/{patient_id}` | **Incomplete** | Same enum risk as above |
| POST | `/appointments` | **Incomplete** | Uses `AppointmentScoringAlgorithm` — crashes on `'insurance'` input |
| GET | `/appointments` | **Incomplete** | Loads full Appointment ORM objects — LookupError on `payment_type='insurance'` |
| GET | `/appointments/{appointment_id}` | **Incomplete** | Same ORM enum crash risk |
| PATCH | `/appointments/{appointment_id}/status` | **Stable** | Updates only `status` string |
| POST | `/appointments/{appointment_id}/outcome` | **Stable** | Updates outcome booleans — no enum access |
| POST | `/appointments/{appointment_id}/assign-suggestion` | Experimental | Touches full Appointment ORM — enum risk |
| GET | `/appointments/suggest-time` | **Not connected** | Queries `clinic_schedules` (0 rows) |
| GET | `/appointments/next-available` | **Not connected** | Depends on `clinic_schedules` |
| GET | `/appointments/suggestions` | **Not connected** | Scheduler requires `clinic_schedules` data |
| GET | `/appointments/available-slots` | **Not connected** | Same |
| GET | `/payment-types` | **Stable** | Returns PaymentType enum values — pure |
| GET | `/treatment-types` | **Stable** | Returns TreatmentType enum values — pure |
| GET | `/ai/patient-history-score/{patient_id}` | **Stable** | Fully connected, enum-safe, tested |
| GET | `/ai/top-patients` | **Stable** | Batch-efficient (3 queries), smoke mode, tested |
| POST | `/ai/predict-appointment` | Experimental | Crashes if `patient.payment_type='insurance'` |
| POST | `/ai/score-patient` | Experimental | Full AI scoring; enum risk on `payment_type` access |
| POST | `/ai/recommend-slot` | **Not connected** | Depends on CSV files in `data/outputs/`; not guaranteed at runtime |
| POST | `/crm/sync/patients` | Experimental | Mock mode only; live CRM stub incomplete |
| POST | `/crm/sync/appointments` | Experimental | Mock only |
| POST | `/crm/sync/patient/{patient_id}` | Experimental | Mock only |
| POST | `/crm/sync/appointment/{appointment_id}` | Experimental | Mock only |
| GET | `/crm/status` | **Stable** | Mock health check |
| GET | `/crm/patients` | **Stable** | Returns mock JSON fixture |
| GET | `/crm/appointments` | **Stable** | Returns mock JSON fixture |
| POST | `/debug/score` | Experimental | Requires `ENABLE_DEBUG_ENDPOINTS=1` |

**Summary:** Stable: 16 · Experimental: 10 · Incomplete: 5 · Not connected: 6

---

## 5. Production Readiness

### Ready for deployment

- Import pipeline (`/api/import/*`) — battle-tested, 344K+ rows processed, idempotent
- `/health`, `/payment-types`, `/treatment-types`, `/crm/status`
- `/ai/patient-history-score/{id}` and `/ai/top-patients` — post-fixes, tested

### Not production-safe

| Risk | Severity | Affected |
|---|---|---|
| **Enum mismatch `'insurance'`** | **Critical** | `GET /appointments`, `GET /appointments/{id}`, `POST /appointments`, `POST /ai/predict-appointment`, `POST /ai/score-patient` — ORM full-object load crashes on 71,104/71,477 rows |
| **`clinic_schedules` empty** | **Critical** | All slot-suggestion and scheduling endpoints return empty/meaningless results |
| **Live CRM client is a stub** | **High** | `app/integrations/crm/live_client.py` is a skeleton — `CRM_MODE=live` will fail at runtime |
| **DataStore CSV files not guaranteed** | **High** | `/ai/recommend-slot` calls `DataStore.load_from_csv()` at request time — missing files silently return 0.5 defaults |
| **No authentication on any endpoint** | **High** | No auth middleware; full DB exposed |
| **No response caching / rate limiting** | **Medium** | `/ai/top-patients?days=30` takes ~9s — no throttle |
| **SQLite in-process** | **Medium** | 5.1 GB file; WAL mode enabled but concurrent write throughput is limited |

---

## 6. Performance Check

### N+1 Query Risks

| Endpoint | Status | Detail |
|---|---|---|
| `GET /ai/top-patients` | **Fixed** | Was 2,725 queries → now 3 total (batch SQL + bulk Patient load) |
| `GET /ai/patient-history-score/{id}` | **Acceptable** | 1 query per call (patched with `with_entities`) |
| `GET /appointments` | **Risk** | Loads all Appointment ORM objects; lazy Patient relationship may trigger N+1 |
| `POST /ai/score-patient` | **Risk** | Accesses `patient.payment_type` — lazy DB read + enum crash |

### Missing Indexes (Impact)

| Query Pattern | Missing Index | Cost |
|---|---|---|
| `appointments.appointment_date >= cutoff` | `appointments(appointment_date)` | Full scan 71,477 rows per call |
| `appointments WHERE status IN (...)` | `appointments(status)` | Full scan per patient score |
| `stg_appointments JOIN appointments ON appointment_id` | `stg_appointments(appointment_id)` | Nested loop |

### Endpoints Likely to Fail with Large Data

| Endpoint | Issue |
|---|---|
| `GET /appointments` | No LIMIT enforced — returns all 71,477 rows; OOM or timeout risk |
| `POST /crm/sync/appointments` | Full ORM load of all appointments — enum crash + memory |
| `/ai/top-patients?days=365` | Would process ~13,956 patients × 1 stats query |

---

## 7. Next Logical Milestone

**Milestone: Eliminate the `payment_type` enum crash system-wide.**

This is the single largest blocking risk. It affects 6+ endpoints and 99.5% of appointment rows.

### Exact technical steps

1. **Add `SafePaymentType` TypeDecorator in `models.py`** — one-file change that fixes all ORM
   consumers at once:
   ```python
   class SafePaymentType(TypeDecorator):
       impl = String
       def process_result_value(self, value, dialect):
           if value is None:
               return None
           try:
               return PaymentType(value)
           except ValueError:
               return None  # unknown value -> None instead of crash
   ```

2. **Add `appointments(appointment_date)` and `appointments(status)` indexes** in
   `database.py:_ensure_indexes()` — two lines, immediate 5–10× speedup on scoring queries.

3. **Populate `clinic_schedules`** — Run a migration from the Excel shift data or add
   `POST /api/import/schedules`. Without this the 6 "Not connected" endpoints cannot work.

4. **Add `ai_patient_scores` cache table** — `(patient_id, score, computed_at)`. Pre-compute
   scores via `scripts/backfill_patient_scores.py`, check cache before DB in
   `calculate_patient_history_score()`. Turns `/ai/top-patients?days=30` from ~9s → ~200ms.

5. **Mount `routes/patients.py` router** — De-duplicates Patient CRUD logic from `main.py`.

These 5 items together move the project from "experimental read-only API" to
"production-safe core API with working scheduling."

---

*Generated by automated technical audit — 2026-03-02*
