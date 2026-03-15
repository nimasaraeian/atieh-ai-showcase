# Reception panel productization – run order and sample responses

## Run order (from repo root)

1. **Apply reception view** (optional; backend reads from `master_patient_profile_v2` directly):
   ```bash
   sqlite3 atieh_clinic_recovery81_test.db < sql/identity_resolution/015_reception_patient_search_view.sql
   ```

2. **Start backend**
   ```bash
   uvicorn main:app --reload
   ```

3. **Start frontend**
   ```bash
   cd frontend && npm run dev
   ```

No core data tables are modified; only the view (and backend/frontend logic) are used.

---

## API

- **GET /api/reception/search-patient?q=&page=1&page_size=50**  
  Search by name, phone, CRM code, or patient ID. Default 50 per page. Sorted by: exact CRM match → exact phone → exact name → link_tier (A first) → payment_rows_count → last_year.

- **GET /api/reception/patient/{patient_id}**  
  All profiles for that patient; includes `multi_crm_for_same_patient_flag`, `linked_crm_codes`, identity/financial summary, review status, years covered.

- **GET /api/reception/crm-code/{crm_code}**  
  Single profile by CRM code.

---

## Review warning rule (frontend and backend)

Show “needs review” **only** when:

- `review_flag === 1`  
  **or**
- `review_reason` is non-empty (after trim).

If `review_flag === 0` and `review_reason` is null/empty → **do not** show the review warning (including for strong/A-tier rows).

---

## Sample JSON

### a) Search result row (one item in `data`)

```json
{
  "patient_id": 12345,
  "crm_patient_code": "80123",
  "patient_name_canonical": "علی محمدی",
  "primary_phone": "09121234567",
  "link_tier": "A",
  "identity_strength_tier": "strong",
  "review_flag": 0,
  "review_reason": null,
  "review_warning": false,
  "payment_rows_count": 45,
  "total_net_received": 12500000.0,
  "last_year": 1403,
  "multi_crm_for_same_patient_flag": false,
  "identity_summary": { "name": "علی محمدی", "primary_phone": "09121234567", "national_id_norm": "0123456789" },
  "financial_summary": { "payment_rows_count": 45, "total_net_received": 12500000.0, "first_year": 1398, "last_year": 1403 },
  "linked_crm_codes": ["80123"]
}
```

Row that **does** need review:

```json
{
  "patient_id": 67890,
  "crm_patient_code": "80456",
  "patient_name_canonical": "علی احمدی",
  "link_tier": "A",
  "review_flag": 1,
  "review_reason": "multiple_candidates_same_tier",
  "review_warning": true,
  "multi_crm_for_same_patient_flag": false
}
```

### b) Search response (full)

```json
{
  "count": 1166,
  "data": [ "... first 50 rows ..." ],
  "query": "علیرضا",
  "page": 1,
  "page_size": 50,
  "total_pages": 24
}
```

### c) Selected patient profile (GET /api/reception/patient/12345)

```json
{
  "patient_id": 12345,
  "profiles": [ "... array of profile objects ..." ],
  "count": 1,
  "multi_crm_for_same_patient_flag": false,
  "linked_crm_codes": ["80123"],
  "identity_summary": { "name": "علی محمدی", "primary_phone": "09121234567", "national_id_norm": "0123456789" },
  "financial_summary": {
    "payment_rows_count": 45,
    "total_net_received": 12500000.0,
    "first_year": 1398,
    "last_year": 1403
  },
  "review_status": { "review_warning": false, "review_reason": null },
  "years_covered": [1398, 1399, 1400, 1401, 1402, 1403],
  "value_band": "A"
}
```

---

## Frontend behavior summary

- **Search:** V2 only; `receptionSearchPatient(q, page, pageSize)` with default `page_size=50`. Show “X results (Y shown)” when total > page_size; “Load more” appends next page.
- **Row badge:** “نیاز به بررسی” only when `showReviewWarning(row)` (review_flag=1 or non-empty review_reason). “چند کد” when `multi_crm_for_same_patient_flag`.
- **Profile panel:** Warning banner only when `showReviewWarning(selectedPatient)`. Show identity tier, review status (سالم vs نیاز به بررسی), payment rows count, years covered. Multi-CRM message when `multi_crm_for_same_patient_flag`.
- **Tier vs review:** Link/identity tier (A/B/C/D) is shown separately from review status; do not infer review from tier.
