# Reception search V2 – frontend condition rules and example response

Reception search uses **master_patient_profile_v2** as the primary source. There is no dependency on `record_no` for determining a valid patient.

---

## 1. Frontend condition rules

| Rule | Implementation |
|------|----------------|
| **Valid identity** | Patient has valid identity if `link_tier != null` OR `crm_patient_code` is non-empty. Use helper `hasV2Identity(p)`. |
| **Show profile** | Show patient profile when `selectedPatient` exists AND (`link_tier` exists OR `crm_patient_code` exists OR legacy `record_no`). |
| **Show warning badge** | When `review_flag === 1`, show a visible badge (e.g. "بررسی" / "Review") next to the name in the list and a short message in the profile panel. |
| **Never "invalid record number"** | Do NOT display "شماره پرونده معتبر برای این بیمار ثبت نشده است" when the selected row has V2 identity (`link_tier` or `crm_patient_code`). Only show that message when the user selected a row that has neither V2 identity nor a numeric `record_no`. |
| **Recommend button** | Enable "get slots" when `selectedPatient` exists AND (V2 identity OR numeric record_no). For V2 rows, pass `crm_patient_code` (or `patient_id`) to the recommend API as the identifier. |
| **Search source** | Call `atiehApi.receptionSearchPatient(q)` only. Results come from `master_patient_profile_v2`. |
| **Selection** | On row click, if the row has `link_tier` or `crm_patient_code`, set profile from the row (identity_summary, financial_summary). Do not call `getPatientByRecordNo` / `getFinancialPatientDetail` for V2 rows. |

---

## 2. Example API response (GET /api/reception/search-patient?q=علی)

```json
{
  "count": 12,
  "query": "علی",
  "data": [
    {
      "patient_id": 12345,
      "crm_patient_code": "80123",
      "patient_name_canonical": "علی محمدی",
      "canonical_patient_name": "علی محمدی",
      "patient_name_key": "علیمحمدی",
      "primary_phone": "09121234567",
      "primary_phone_norm": "09121234567",
      "national_id_norm": "0123456789",
      "canonical_national_id_norm": "0123456789",
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
      "linked_crm_codes": ["80123"]
    },
    {
      "patient_id": 67890,
      "crm_patient_code": "80456",
      "canonical_patient_name": "علی احمدی",
      "primary_phone_norm": "09129876543",
      "canonical_national_id_norm": null,
      "payment_rows_count": 12,
      "total_net_received": 3000000.0,
      "identity_strength_tier": "medium",
      "link_tier": "A",
      "review_flag": 1,
      "review_reason": "multiple_candidates_same_tier",
      "review_warning": true,
      "linked_crm_codes": ["80456"]
    }
  ]
}
```

---

## 3. Backend search fields

Search uses **master_patient_profile_v2** and matches on:

- **canonical_patient_name** (column: `patient_name_canonical`) – LIKE
- **primary_phone_norm** (column: `primary_phone`) – normalized exact or LIKE
- **crm_patient_code** – exact or LIKE
- **canonical_national_id_norm** (column: `national_id_norm`) – exact when query is 10 digits

Plus numeric query: exact match on `patient_id` when query is digits.

---

## 4. SQL view (reception_patient_search_view)

View columns (from master_patient_profile_v2):

- patient_id  
- crm_patient_code  
- canonical_patient_name (alias of patient_name_canonical)  
- primary_phone_norm (alias of primary_phone)  
- canonical_national_id_norm (alias of national_id_norm)  
- payment_rows_count  
- total_net_received  
- positive_net_received_sum  
- negative_net_received_sum  
- identity_strength_tier  
- link_tier  
- review_flag  

Apply view (from repo root):

```bash
sqlite3 atieh_clinic_recovery81_test.db < sql/identity_resolution/015_reception_patient_search_view.sql
```
