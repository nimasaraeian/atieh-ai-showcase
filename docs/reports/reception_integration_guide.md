# Reception integration guide – V2 identity layer

Product integration for reception panel using **master_patient_profile_v2** and reception API. Do not expand identity logic; use this as the search/display layer.

---

## Run order (from repo root)

1. **Apply view** (optional; API reads from `master_patient_profile_v2` directly):
   ```bash
   sqlite3 atieh_clinic_recovery81_test.db < sql/identity_resolution/015_reception_patient_search_view.sql
   ```

2. **Start backend** (reception routes are included):
   ```bash
   uvicorn main:app --reload
   ```

3. **Frontend**: call `GET /api/reception/search-patient?q=...`, `GET /api/reception/patient/{id}`, `GET /api/reception/crm-code/{code}`.

---

## API routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reception/search-patient?q=&limit=50&offset=0` | Search by name, phone, CRM code, or patient_id |
| GET | `/api/reception/patient/{patient_id}` | All linked profiles for one patient |
| GET | `/api/reception/crm-code/{crm_code}` | Single profile by CRM code |

---

## Sample JSON response payloads

### GET /api/reception/search-patient?q=علی

```json
{
  "count": 12,
  "query": "علی",
  "data": [
    {
      "patient_id": 12345,
      "crm_patient_code": "80123",
      "patient_name_canonical": "علی محمدی",
      "patient_name_key": "علیمحمدی",
      "primary_phone": "09121234567",
      "national_id_norm": "0123456789",
      "payment_rows_count": 45,
      "total_net_received": 12500000.0,
      "positive_net_received_sum": 13000000.0,
      "negative_net_received_sum": -500000.0,
      "first_year": 1398,
      "last_year": 1403,
      "identity_strength_tier": "strong",
      "link_tier": "A",
      "link_rule": "national_id_exact",
      "review_flag": 0,
      "review_reason": null,
      "created_at": "2026-03-15 12:00:00",
      "identity_summary": {
        "name": "علی محمدی",
        "name_key": "علیمحمدی",
        "primary_phone": "09121234567",
        "national_id_norm": "0123456789"
      },
      "financial_summary": {
        "payment_rows_count": 45,
        "total_net_received": 12500000.0,
        "positive_net_received_sum": 13000000.0,
        "negative_net_received_sum": -500000.0,
        "first_year": 1398,
        "last_year": 1403
      },
      "confidence": {
        "link_tier": "A",
        "link_rule": "national_id_exact",
        "identity_strength_tier": "strong"
      },
      "review_warning": false,
      "review_reason": null,
      "linked_crm_codes": ["80123"]
    }
  ]
}
```

### GET /api/reception/search-patient?q=09121234567

Same structure; `data` contains profiles matching that phone (and possibly name/crm if query matches multiple).

### GET /api/reception/patient/12345

```json
{
  "patient_id": 12345,
  "profiles": [
    {
      "patient_id": 12345,
      "crm_patient_code": "80123",
      "patient_name_canonical": "علی محمدی",
      "identity_summary": { ... },
      "financial_summary": { ... },
      "confidence": { "link_tier": "A", "link_rule": "crm_record_plus_name_key", "identity_strength_tier": "strong" },
      "review_warning": false,
      "linked_crm_codes": ["80123"]
    }
  ],
  "count": 1
}
```

### GET /api/reception/crm-code/80123

```json
{
  "crm_patient_code": "80123",
  "found": true,
  "profile": {
    "patient_id": 12345,
    "crm_patient_code": "80123",
    "patient_name_canonical": "علی محمدی",
    "review_warning": false,
    "identity_summary": { ... },
    "financial_summary": { ... },
    "confidence": { ... },
    "linked_crm_codes": ["80123"]
  }
}
```

### GET /api/reception/crm-code/99999 (not found)

```json
{
  "crm_patient_code": "99999",
  "found": false,
  "profile": null
}
```

### Item with review warning (review_flag = 1)

In any of the above, when `review_flag === 1`:

```json
{
  "review_flag": 1,
  "review_reason": "multiple_candidates_same_tier",
  "review_warning": true,
  ...
}
```

---

## UI safety rules

1. **Never auto-merge** – Do not merge identities or change links from the UI. Resolution is backend-only.
2. **Show warning badge** – If `review_warning === true` (or `review_flag === 1`), show a visible badge (e.g. “نیاز به بررسی”) so staff know the link is uncertain.
3. **Use V2 as search/display layer** – Reception search and profile display must use these APIs (and thus `master_patient_profile_v2`). Do not mix with old record_no-only or V1-only flows for the same screen.
4. **Unresolved identities must not break the UI** – If a search returns no rows or CRM code not found, show an empty state or “یافت نشد”; do not throw or block the panel. Unlinked payment identities stay in `payment_identity_master` and are not shown until linked.

---

## Frontend integration notes

- **Base URL**: same as rest of API (e.g. `VITE_API_BASE` or current origin).
- **Search**: `GET /api/reception/search-patient?q=${encodeURIComponent(q)}&limit=50&offset=0`. Use `data` for the list; each item has `identity_summary`, `financial_summary`, `confidence`, `review_warning`, `linked_crm_codes`.
- **Patient detail**: `GET /api/reception/patient/${patient_id}`. Use `profiles` array (one or more profiles per patient).
- **CRM lookup**: `GET /api/reception/crm-code/${encodeURIComponent(crm_code)}`. Use `profile` when `found === true`.
- **Display**: Prefer `patient_name_canonical` for display; use `financial_summary` for payment stats; use `review_warning` to show the badge.
- **Errors**: On 4xx/5xx or network error, show a generic error message and optionally a retry; do not auto-merge or overwrite data.

**Optional atiehApi helpers** (in `frontend/src/services/atiehApi.js`):

- `atiehApi.receptionSearchPatient(q, limit, offset)` → `{ count, data, query }`
- `atiehApi.receptionGetPatient(patientId)` → `{ patient_id, profiles, count }`
- `atiehApi.receptionGetByCrmCode(crmCode)` → `{ crm_patient_code, found, profile }`

---

## Deliverables summary

| Deliverable | Location |
|-------------|----------|
| SQL view | `sql/identity_resolution/015_reception_patient_search_view.sql` |
| Backend service | `app/api/reception/service.py` |
| API routes | `app/api/reception/routes.py` |
| Router registration | `main.py` (reception_router) |
| Sample payloads | This document |
| Frontend guide | This document (UI safety + integration notes) |
