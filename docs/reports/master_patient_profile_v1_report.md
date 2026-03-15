# Master Patient Profile V1 Report

Final safe, product-ready derived layer for reception/backend integration.

**Generated:** 2026-03-15T15:30:36.682783

## 1. Summary

| Metric | Value |
|--------|-------|
| Total rows in **master_patient_profile_v1** | 32,595 |
| Total rows in **master_patient_profile_review_queue** | 126,500 |
| Distinct **patient_id** in V1 | 27,661 |
| Distinct **crm_patient_code** in V1 | 32,595 |
| Total **payment_rows_count** covered by V1 | 360,647 |
| Total payment rows (payments_crm_code_all_years, with code) | 876,054 |
| **Percentage of payments covered by V1** | 41.17% |

## 2. Breakdown by link_confidence (V1)

| link_confidence | Count |
|------------------|-------|
| medium | 32,595 |

## 3. Breakdown by link_rule (V1)

| link_rule | Count |
|-----------|-------|
| name_exact | 32,595 |

## 4. Exclusions (review_queue)

| Reason | Count |
|--------|-------|
| common_name_key (risky name_key duplication) | 0 |
| was_ambiguous (code had ambiguity history) | 0 |
| no_financial_aggregate | 0 |
| multiple_patients_per_code | 126,500 |
| multiple_codes_per_patient | 0 |

## 5. Recommendation

**Safe for reception panel** – use master_patient_profile_v1 for search by name, phone, CRM code; use review_queue for manual resolution of uncertain cases.

---

## Sample query patterns for backend/API

### Search by patient name (canonical or name_key)
```sql
SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, primary_phone, payment_rows_count, total_net_received
FROM master_patient_profile_v1
WHERE patient_name_key = :name_key
   OR patient_name_canonical LIKE '%' || :query || '%';
```

### Search by phone
```sql
SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, primary_phone, payment_rows_count
FROM master_patient_profile_v1
WHERE primary_phone = :phone_norm;
-- Or search inside all_phones_json if needed (JSON array).
```

### Search by CRM code
```sql
SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, primary_phone,
       payment_rows_count, total_net_received, first_year, last_year, link_confidence, link_rule
FROM master_patient_profile_v1
WHERE crm_patient_code = :crm_code;
```

### Fetch full patient profile by patient_id
```sql
SELECT master_profile_id, patient_id, crm_patient_code, patient_name_canonical, patient_name_key,
       primary_phone, all_phones_json, national_id_norm,
       payment_rows_count, total_net_received, positive_net_received_sum, negative_net_received_sum,
       first_year, last_year, link_confidence, link_rule, ambiguity_flag, ambiguity_reason
FROM master_patient_profile_v1
WHERE patient_id = :patient_id;
```

---

## Run order (from repo root)

1. Apply schema: `sqlite3 atieh_clinic_recovery81_test.db < sql/identity_resolution/013_master_patient_profile_v1_schema.sql`
2. Build V1: `python scripts/build_master_patient_profile_v1.py`
3. Generate this report: `python scripts/master_patient_profile_v1_stats.py`

## Validate final counts (SQLite)

```sql
SELECT COUNT(*) AS v1_rows FROM master_patient_profile_v1;
SELECT COUNT(DISTINCT patient_id) AS distinct_patient_id FROM master_patient_profile_v1;
SELECT COUNT(DISTINCT crm_patient_code) AS distinct_crm_code FROM master_patient_profile_v1;
SELECT SUM(payment_rows_count) AS payment_rows_covered FROM master_patient_profile_v1;
SELECT COUNT(*) AS review_queue_rows FROM master_patient_profile_review_queue;
SELECT COUNT(*) AS total_payment_rows_with_code FROM payments_crm_code_all_years
  WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> '';
SELECT (SELECT SUM(payment_rows_count) FROM master_patient_profile_v1) * 100.0 / NULLIF(
  (SELECT COUNT(*) FROM payments_crm_code_all_years WHERE parse_status = 'ok' AND extracted_crm_code IS NOT NULL AND TRIM(extracted_crm_code) <> ''), 0) AS coverage_pct;
```
