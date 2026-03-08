# Atieh Dental Clinic — AI Data Intelligence System
## Complete Technical Architecture Report

---

## 1️⃣ PROJECT OVERVIEW

### What This System Does

The Atieh system is an **AI-driven data intelligence platform** for a dental clinic. It ingests historical CRM data (appointments, payments) from Excel exports, resolves patient identity across disjoint data sources, builds a financial and behavioral intelligence layer, and exposes APIs for:

- **Value-based patient prioritization** — financial scoring, VIP detection, scheduling priority
- **Slot recommendation** — time-value-slot (TVS) engine for appointment scheduling
- **Financial segmentation** — tiering patients (VIP/HIGH/MEDIUM/LOW) for outreach and scheduling

### Problem It Solves

1. **Disparate data** — Appointments (who showed up, when) and payments (who paid, how much) live in separate Excel files with no common key (e.g., patient file number appears in payments but not in appointment history).
2. **No unified patient view** — The clinic cannot see lifetime value, retention, or risk per patient without manual joining.
3. **Suboptimal scheduling** — High-value and loyal patients are not prioritized when slots are allocated.
4. **Missing financial signals** — Revenue, payer mix, and recency are not integrated into scheduling decisions.

### Main Objective

Build a **reliable identity-linked intelligence layer** that connects:

- Payment rows (with `record_no` and amounts)
- Appointment rows (with name, phone, date)
- Patient entities (scheduling system `patient_id`)

…and then compute **patient lifetime value, financial score, and risk indicators** for use in scheduling, prioritization, and AI decision support.

### Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAW DATA LAYER                                       │
│  Excel: payments_<YEAR>_full.xlsx | history/<YEAR>/*.xlsx (appointments)         │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│                              ETL / IMPORT PIPELINE                                │
│  payments_importer → stg_payments | history_importer → stg_appointments          │
│  Build payments_clean, financial_patient_dim, patient_record_map                 │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│                              BRIDGE PIPELINE (per-year)                           │
│  bridge_<YEAR>_payment_appointment | patient_recordno_map_<YEAR>                  │
│  Tier A/B/C: date+name+phone, date+name unique, name+phone                       │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│                              AGGREGATION & FEATURE LAYER                          │
│  patient_financial_summary | patient_features | financial_value_score             │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│                              DECISION / AI LAYER                                  │
│  Financial boost API | Slot recommender | Patient scoring                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

- **Database**: SQLite (`atieh_clinic.db`) with WAL mode  
- **Backend**: FastAPI  
- **Data processing**: pandas, openpyxl, jdatetime (Jalali dates)

---

## 2️⃣ REPOSITORY STRUCTURE

| Directory | Purpose |
|-----------|---------|
| **`app/`** | Core application: API, engine, importers, loaders, schemas, utils |
| **`app/importers/`** | ETL: `history_importer.py` (appointments), `payments_importer.py` (payments), `common/` (normalize, hashing, shamsi) |
| **`app/engine/`** | Scheduling engine: TVS allocator, slot fit, patient value, recommender |
| **`app/api/`** | REST routes: import, AI financial, engine recommend-slot |
| **`app/db/migrations/`** | 16 SQL migrations for tables, views, indexes |
| **`app/ai/`** | Financial boost logic: `financial_boost.py` |
| **`config/`** | `weights.yaml` — engine weights, penalties, slot settings |
| **`scripts/`** | Bridge scripts (`bridge_<YEAR>_payment_appointment.py`), backfill, query utilities |
| **`tools/`** | RecordNo pipeline: `build_appointment_recordno_bridge.py`, `build_patient_recordno_map.py`, `build_patient_financial_summary.py` |
| **`data/inputs/`** | Raw Excel: `payments/`, `history/<YEAR>/` |
| **`data/outputs/`** | Generated CSVs for engine (doctor shifts, services, etc.) |
| **`data/reference/`** | Catalogs: services, insurances |
| **`tests/`** | Pytest tests |
| **`docs/`** | PATIENT_SCORING, RECORDNO_RESOLUTION_PIPELINE, BRIDGE_PIPELINE_RUNBOOK, etc. |

Root files: `main.py` (FastAPI entry), `models.py` (SQLAlchemy ORM), `database.py`, `ai_brain.py`, `scoring_algorithm.py`, `appointment_scheduler.py`.

---

## 3️⃣ DATA PIPELINE ARCHITECTURE

### Raw Sources

| Source | Location | Contents |
|--------|----------|----------|
| **Payments** | `data/inputs/payments/payments_<YEAR>_full.xlsx` | Patient name, phone, date, amounts, insurer; `record_no` in name or column |
| **Appointments** | `data/inputs/history/<YEAR>/*.xlsx` | Patient name, phone, date, doctor, service; **no record_no** |

Payments use Shamsi (Jalali) dates; both sources use Persian headers with Arabic/Persian character variants.

### Processing Stages

1. **Cleaning**  
   - Header normalization: remove quotes, map `ي`→`ی`, `ك`→`ک`  
   - Persian/Arabic digits → ASCII  
   - Phone parsing: `;`/`,`-separated, multiple numbers per cell  
   - Extract `record_no` from `Name(record_no)` suffix or dedicated column  

2. **Normalization**  
   - `app.importers.common.normalize`: `normalize_text`, `normalize_phone`, `extract_digits_only`  
   - `history_importer`: `normalize_fa_key`, `normalize_phone_local`, `upsert_patient` (by national_id, phone, name)  
   - `payments_importer`: insurer parsing (`آزاد`→cash, `(30 %)`→patient share pct)  

3. **Identity resolution**  
   - `upsert_patient`: match by national_id → phone → create new  
   - Bridge: link payment `record_no` to appointment rows by date+name+phone  

4. **Bridge pipeline**  
   - Per-year scripts: `scripts/bridge_<YEAR>_payment_appointment.py`  
   - Load payments + appointments Excel → build `PayRow` / `ApptRow` → run tier logic → write `bridge_<YEAR>_payment_appointment`, `bridge_<YEAR>_review`, `patient_recordno_map_<YEAR>`  

### Tier Logic

| Tier | Match criteria | Confidence | When used |
|------|----------------|------------|-----------|
| **A** | Date + name + overlapping phone | 1.0 | Exact date+name+phone match |
| **B** | Date + name, unique on both sides | 0.9 | No phone overlap; only one payment and one appointment per (date, name) |
| **C** | Name + overlapping phone | 0.8 | Date missing or weak |

**Why tiers matter**  
- Appointment files lack `record_no`; only name and phone are available.  
- Tier A is strongest; B handles cases without phone; C handles missing date.  
- Tier C is more ambiguous; multiple matches go to `bridge_<YEAR>_review`.  

**Operational results (per BRIDGE_PIPELINE_RUNBOOK)**  
- 1403: ~34.5K accepted, ~11.8K distinct record_no (A: 31.8K, B: 1.7K, C: 0.99K)  
- 1402: ~30K accepted  
- 1400: ~16.4K  
- 1396: 104 (low CRM coverage for that year)  

---

## 4️⃣ DATABASE STRUCTURE

### Core Tables (ORM)

| Table | Purpose |
|-------|---------|
| **patients** | Master: id, name, phone, national_id, payment_type, first_visit_date, lifetime_value_score |
| **appointments** | Scheduling: patient_id, appointment_date, treatment_type, payment_type, priority_score, status, ai_priority_score, did_patient_show_up, paid_on_time, final_amount_paid |
| **clinic_schedules** | Working hours by day |

### Staging

| Table | Purpose |
|-------|---------|
| **stg_appointments** | Raw history rows: row_json, parse_status, patient_id, appointment_id |
| **stg_payments** | Raw payment rows: patient_name_raw, phone_raw, insurer, amounts, insurer_name_norm, payer_source_norm |

### Financial / Identity

| Table | Purpose |
|-------|---------|
| **payments_clean** | Normalized payments: record_no, patient_id, amounts, payer_source_norm |
| **financial_patient_dim** | Dimension by record_no: name_clean, phone_norm |
| **patient_record_map** | record_no → patient_id (legacy / alternate mapping) |
| **patient_recordno_map** | record_no ↔ patient_id with match_method, confidence |
| **patient_financial_summary** | Aggregates per record_no: lifetime_net_received, txn counts, financial_value_score |

### Bridge (per year)

| Table | Purpose |
|-------|---------|
| **bridge_<YEAR>_payment_appointment** | Links record_no to appointment rows: appointment_patient_key, match_method, confidence |
| **bridge_<YEAR>_review** | Ambiguous or unresolved cases |
| **patient_recordno_map_<YEAR>** | Year-specific record_no ↔ identity mapping |

### Views

| View | Purpose |
|------|---------|
| **v_financial_for_engine** | patient_id + financial metrics (via patient_record_map) |
| **v_financial_for_engine_recordno** | record_no + financial metrics (used by AI APIs) |
| **v_patients_with_financial** | Patients with linked financial data |
| **v_patients_financial_resolved** | patients + record_no + financial summary |

### Other

| Table | Purpose |
|-------|---------|
| **patient_features** | visit counts, tenure_days, last_visit_days, lifetime_value, frequency |
| **patient_identifiers** | Identity map: record_no, phone, national_id per patient |
| **record_no_patient_map** | record_no → patient mapping |
| **engine_scoring_config** | FIN_MAX_BOOST, FIN_MAX_BOOST_IF_URGENT |
| **import_runs** | Import history |

### Relational Flow

```
patients ←──── appointments
   ↑                 ↑
   │                 │
   │         stg_appointments
   │
patient_recordno_map ──→ patient_financial_summary
   ↑                              ↑
   │                              │
bridge_<YEAR>_payment_appointment  v_financial_for_engine_recordno
   ↑
payments_clean ←── stg_payments
```

---

## 5️⃣ PATIENT IDENTITY RESOLUTION

### Normalization

- **Persian names**: Arabic `ي`→`ی`, `ك`→`ک`; strip ZWNJ; collapse spaces  
- **Phones**: Split on `;`, `,`, `/`, `|`; keep 11-digit 09…; support `+98`, `98`, `9`, `09`  
- **Record_no**: From `Name(record_no)` or dedicated column  

### Linking Logic

1. **Payments → appointments**  
   Bridge scripts match on:  
   - Tier A: (date, name, phone overlap)  
   - Tier B: (date, name) when unique  
   - Tier C: (name, phone overlap)  

2. **Record_no → patient**  
   - `patient_recordno_map` (or per-year map) stores record_no → patient_id with match_method and confidence  
   - Parsed name and phone from bridge are used as evidence  

3. **record_no mapping**  
   - Payments always have record_no; appointments do not  
   - Bridge seeds mapping from payment-side identity to appointment-side identity  

### Reliability

- **Strengths**: Tier A is very reliable; B works when names are unique on date; C adds matches when date is missing  
- **Limitations**:
  - Same name + different phones can collide
  - Tier C can be ambiguous → review table
  - Year 1396: only 111 appointment rows in CRM → low coverage by design  
  - Some years (e.g. 1397, 1401) have no data  

---

## 6️⃣ FEATURE ENGINEERING

### Engineered Features

| Source | Feature | Description |
|--------|---------|-------------|
| **AIBrain.extract_features()** | num_prev_appointments, num_completed, completion_rate, num_no_show, num_late_payments, lifetime_months | From appointments (completed/cancelled) |
| **patient_financial_summary** | lifetime_txn_count, lifetime_net_received, recent_txn_count, recent_net_received, cash_txn_count, insurance_txn_count, financial_value_score | From payments_clean |
| **patient_features (SQL)** | visits_total, tenure_days, last_visit_days, lifetime_value, frequency | From appointments |
| **Backfill scoring** | patient_priority_score, insurance_score, treatment_score, tenure_score, frequency_score | From appointments + reference catalogs |

### Financial Value Score

Computed in `tools/build_patient_financial_summary.py`:

```
monetary   = log1p(net_sum) / max_log_net
frequency  = txn_count / max_txn
recent_m   = log1p(recent_net) / max_recent
mix_boost  = 0.1 * cash_rate
neg_penalty = min(0.5, neg_txn_rate)

score = 0.55*monetary + 0.25*frequency + 0.20*recent_m + mix_boost - neg_penalty
```

### Use in AI Models

Features support:

- **Risk**: no-show, late payment
- **Value**: lifetime spend, tenure, completion rate
- **Retention**: last_visit_days, frequency
- **Segmentation**: financial_value_score → VIP/HIGH/MEDIUM/LOW

Current logic is rule-based; the schema is ready for ML models (e.g. scikit-learn, XGBoost) on top of these features.

---

## 7️⃣ AI / DECISION ENGINE

### Patient Prioritization

- **API**: `GET /api/ai/priority/record-no/{record_no}`  
- **Logic**: `apply_financial_boost()` in `app/ai/financial_boost.py`  
  - Loads `financial_value_score` (0–1) for record_no  
  - Boost = `FIN_MAX_BOOST * financial_value_score` (default 12)  
  - If urgent: `FIN_MAX_BOOST_IF_URGENT` (default 3)  
  - `ai_priority_score = base_score + boost`  

### Financial Scoring & Tiers

- **Tiers** (in `ai_financial_recordno.py`):
  - VIP: score ≥ 0.85  
  - HIGH: score ≥ 0.70  
  - MEDIUM: score ≥ 0.50  
  - LOW: &lt; 0.50  

- **Action hints** (Persian): e.g. "تماس فوری + نوبت نزدیک" for VIP, "اولویت پایین" for LOW  

### Value-Based Scheduling

- **Engine**: `app/engine/` — TVS (Time-Value-Slot) allocator, slot_fit, patient_value  
- **Config**: `config/weights.yaml` — currently patient value weights set to 0 (phase 1 operational mode: slot fit only)  
- **APIs**: `POST /ai/engine/recommend-slot`; `GET /ai/engine/catalog/services`, `/catalog/insurances`  

### Retention Prediction

- AIBrain `extract_features` and `predict_risk_and_value` compute completion_rate, no_show rate, late payment rate  
- Used for `POST /ai/score-patient` and `POST /ai/recommend-slot`  

---

## 8️⃣ DATA QUALITY & LIMITATIONS

| Limitation | Impact |
|------------|--------|
| **Missing CRM data in early years** | 1396: 111 appointment rows; 1397, 1401: no data; reduced match coverage |
| **Partial appointment history** | Some years have sparse appointment files; bridge matches are limited |
| **Noisy Persian text** | Variants of ي/ی, ك/ک, quotes; normalization helps but edge cases remain |
| **Incomplete phones** | Landlines, missing numbers; Tier A/B/C mitigate but not fully |
| **Multiple phones per row** | `;`-separated; bridge uses overlap; collisions possible |
| **record_no in payments only** | Identity resolution depends on name+phone+date matching |
| **Duplicate names** | Tier B requires uniqueness; ambiguous cases go to review |
| **No real-time sync** | Batch Excel imports; no live CRM integration |

---

## 9️⃣ STRENGTHS OF THE SYSTEM

1. **Multi-year behavioral dataset** — 8+ years (1395–1404) of payments and appointments  
2. **Robust identity pipeline** — Tiered bridge logic with confidence and review handling  
3. **Integrated financial + medical data** — Payments and appointments linked for value and risk analysis  
4. **AI-ready feature layer** — patient_features, patient_financial_summary, extract_features  
5. **Record_no-native APIs** — Works even when patient_id mapping is incomplete  
6. **Configurable scoring** — engine_scoring_config, weights.yaml  
7. **Operational documentation** — BRIDGE_PIPELINE_RUNBOOK, RECORDNO_RESOLUTION_PIPELINE, PATIENT_SCORING  
8. **Idempotent migrations** — schema_migrations, safe re-runs  

---

## 🔟 POTENTIAL IMPROVEMENTS

| Improvement | Rationale |
|-------------|-----------|
| **PostgreSQL migration** | Concurrency, JSON support, full-text search, production robustness |
| **Unified bridge table** | Single `bridge_payment_appointment_all` instead of per-year tables; simpler queries |
| **ML prediction models** | Train on features for retention, no-show, LTV; replace rule-based scoring |
| **Real-time scheduling optimizer** | Use live slots + financial score for next-best-slot |
| **REST API consolidation** | Standardize `/api/v1/` structure; OpenAPI documentation |
| **Incremental import** | Delta loads instead of full Excel re-import |
| **Data validation layer** | Great Expectations or custom checks on stg_* and payments_clean |
| **CRM integration** | Live sync instead of manual Excel upload |
| **Unified patient_recordno_map** | Merge per-year maps into one table with source_year |
| **Audit logging** | Track who changed what and when for compliance |

---

## 1️⃣1️⃣ BUSINESS VALUE

| Use case | Value |
|----------|-------|
| **Patient value segmentation** | VIP/HIGH/MEDIUM/LOW for targeted outreach and care |
| **Revenue forecasting** | Aggregate by tier and period from patient_financial_summary |
| **Scheduling optimization** | Prioritize high-value patients; reduce no-shows via risk signals |
| **High-value patient identification** | Top record_no by financial_value_score; action hints |
| **Retention monitoring** | last_visit_days, frequency, completion_rate for churn risk |
| **Payer mix analysis** | Cash vs insurance from payer_source_norm |
| **Treatment value** | Link treatments to financial outcomes via appointments |

**ROI levers**:

- Better slot utilization (prioritizing high-value patients)  
- Reduced no-shows (risk-based reminders)  
- Higher LTV through retention actions  
- More efficient staff scheduling  

---

## 1️⃣2️⃣ FINAL ARCHITECTURE SUMMARY

```
RAW DATA (Excel)
    │
    ▼
CLEANING (normalize headers, Persian/Arabic, phones, dates)
    │
    ▼
IMPORT (stg_payments, stg_appointments → payments_clean, patients, appointments)
    │
    ▼
IDENTITY RESOLUTION (patient upsert: national_id → phone → create)
    │
    ▼
BRIDGE PIPELINE (per-year: Tier A/B/C match payment ↔ appointment)
    │
    ▼
AGGREGATION (patient_financial_summary, patient_features)
    │
    ▼
DECISION INTELLIGENCE (financial boost, tiering, slot recommendation)
    │
    ▼
APIs (priority by record_no, top financial, recommend-slot)
```

The system provides a **production-ready foundation** for AI-driven clinic operations, with a clear path to ML models, real-time integration, and a more scalable database.

---

*Report generated from full repository analysis. Last updated: March 2026.*
