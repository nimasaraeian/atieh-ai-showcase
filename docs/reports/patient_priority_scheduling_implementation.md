# Patient Priority Scheduling Layer – Implementation Summary

## A) Architecture Changes

- **patient_priority_profile_v1**  
  SQL view (raw inputs) in the financial/recovery DB. Joins `master_patient_profile_v2` and `patient_insurance_profile_v2`; pulls visit count, first/last year, lifetime_net_received, insurance_name, last_payment_date from payments.

- **Scoring (Python)**  
  `app/engine/patient_priority.py` loads a row from the view by `record_no` / `crm_patient_code` / `patient_id`, then computes:
  - **insurance_score** (0–100): cash=100, else lookup `insurance_priority_rank` or 50.
  - **visit_score**: log-normalized visit_count.
  - **relationship_score**: relationship_years × 5 (capped at 100).
  - **financial_score**: log-normalized lifetime_net_received.
  - **recency_score**: from last_payment_date (more recent ⇒ higher).
  - **patient_priority_score**: weighted sum (25% insurance, 20% visit, 15% relationship, 30% financial, 10% recency), 0–100.
  - **patient_priority_tier**: P1–P7 from score bands (see config).
  - **scheduling_window_days**: (min_days, max_days) per tier (P1: 0–3, P2: 0–5, … P7: 14+).

- **Config**  
  `app/engine/patient_priority_config.py`: weights, tier bands, scheduling windows (no magic numbers in recommender).

- **Recommender**  
  `app/engine/db_schedule_recommender.py`:
  - Loads priority profile via `get_patient_priority_profile(record_no, crm_patient_code)`.
  - Filters slots by scheduling window (slot date within [today+min_days, today+max_days]).
  - Optional **doctor filter**: if `doctor_id` in payload, `WHERE d.doctor_id = ?`.
  - Adds to response: `patient_priority_profile`, `preferred_doctor_filter`, and per-slot `patient_priority_tier`, `scheduling_window_days`, `reasons` (including PATIENT_TIER_*, SCHEDULING_WINDOW_DAYS_*, PREFERRED_DOCTOR_FILTER).

- **Reception API**  
  `get_reception_patient_by_id` and `get_reception_patient_by_crm_code` attach `patient_priority_profile` when the view/engine is available.

- **Frontend**  
  - Profile: “Patient scheduling priority” block (insurance score, visit count, relationship years, financial contribution, priority score, tier, scheduling window).
  - Recommend payload: `record_no`, `crm_patient_code`, `doctor_id` (optional).
  - After recommend: show tier, scheduling window days, and whether doctor filter was used.

## B) Files Created / Modified

| Path | Action |
|------|--------|
| `app/engine/patient_priority_config.py` | Created – weights, tiers, windows |
| `app/engine/patient_priority.py` | Created – load view, compute scores/tier/window |
| `sql/patient_priority_profile_v1_view.sql` | Created – view definition |
| `app/engine/db_schedule_recommender.py` | Modified – priority profile load, window filter, doctor filter, response fields |
| `app/api/reception/service.py` | Modified – attach `patient_priority_profile` to profile responses |
| `app/api/routes/engine.py` | Modified – pass `crm_patient_code`, `doctor`, `doctor_id` to recommender |
| `frontend/src/pages/ReceptionistPage.jsx` | Modified – priority block, doctor dropdown, recommend payload, recommendation meta |
| `frontend/src/locales/fa/common.json` | Modified – reception.priority.*, doctorOptional, allDoctors, doctorFilter |
| `frontend/src/locales/en/common.json` | Modified – same keys |

## C) Migration / SQL

Run once (PowerShell):

```powershell
Get-Content sql/patient_priority_profile_v1_view.sql -Raw | sqlite3 atieh_clinic_recovery81_test.db
```

Requires same DB that has `master_patient_profile_v2` and `patient_insurance_profile_v2` (and `payments_unified_staging` for the subquery). No change to staging tables.

## D) API Contract

- **GET /api/reception/patient/{patient_id}**  
  Response may include `patient_priority_profile`: insurance_name, insurance_score, visit_count, visit_score, first_visit_year, relationship_years, relationship_score, total_payments, payment_count, lifetime_net_received, financial_score, last_payment_date, recency_score, patient_priority_score, patient_priority_tier, patient_priority_tier_label, scheduling_window_days, scheduling_window_min_days, scheduling_window_max_days, recommended_priority_band, explanation_json.

- **GET /api/reception/crm-code/{crm_code}**  
  Same `patient_priority_profile` when available.

- **POST /ai/engine/recommend-slot**  
  - Body may include `record_no`, `crm_patient_code`, `doctor_id` (optional).
  - Response: `patient_priority_profile`, `preferred_doctor_filter`, `patient_context` (with patient_priority_tier, scheduling_window_days). Each slot: `patient_priority_tier`, `scheduling_window_days`, `preferred_doctor_filter`, `reasons` (including tier/window/doctor).

## E) How to Test End-to-End

1. Apply view (see Migration above).
2. Start backend and frontend.
3. Reception: search patient → select a patient with V2 identity (or by record_no).
4. Confirm profile shows “Patient scheduling priority” with score, tier, scheduling window when priority profile is loaded.
5. Set service, insurance, optional doctor, preferred day → “Get AI Recommended Slots”.
6. Confirm response includes `patient_priority_profile` and slots only within the tier’s scheduling window; if doctor_id was sent, only that doctor’s slots.
7. Check each slot’s `reasons` for PATIENT_TIER_*, SCHEDULING_WINDOW_DAYS_*, and optionally PREFERRED_DOCTOR_FILTER.

## F) Example Response Payload (recommend-slot)

```json
{
  "ok": true,
  "source": "doctor_time_slots",
  "count": 3,
  "preferred_day_input": "Saturday",
  "preferred_day_mapped": "شنبه",
  "record_no_used": "80123",
  "preferred_doctor_filter": false,
  "patient_priority_profile": {
    "patient_id": 42,
    "crm_patient_code": "80123",
    "patient_name": "علی محمدی",
    "insurance_name": "تامین اجتماعی",
    "insurance_score": 50.0,
    "visit_count": 24,
    "visit_score": 72.3,
    "first_visit_year": 1398,
    "relationship_years": 6,
    "relationship_score": 30.0,
    "lifetime_net_received": 12500000.0,
    "financial_score": 65.2,
    "last_payment_date": "1403/05/15",
    "recency_score": 80.0,
    "patient_priority_score": 58.5,
    "patient_priority_tier": "P3",
    "patient_priority_tier_label": "High",
    "scheduling_window_days": 7,
    "scheduling_window_min_days": 0,
    "scheduling_window_max_days": 7
  },
  "patient_context": {
    "patient_priority_tier": "P3",
    "scheduling_window_days": 7
  },
  "recommendations": [
    {
      "slot_id": 101,
      "doctor_id": 1,
      "doctor_name": "دکتر احمدی",
      "date": "2025-03-15",
      "time": "09:00",
      "score": 0.82,
      "patient_priority_tier": "P3",
      "scheduling_window_days": 7,
      "preferred_doctor_filter": false,
      "reasons": ["PATIENT_TIER_P3", "SCHEDULING_WINDOW_DAYS_7", "EARLY_SLOT"]
    }
  ]
}
```
