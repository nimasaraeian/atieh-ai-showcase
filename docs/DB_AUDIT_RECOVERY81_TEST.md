# Database Audit Report: atieh_clinic_recovery81_test.db

**Purpose:** Identity resolution and payment recovery audit.  
**Scope:** Table inventory, schemas, row counts, indexes, payment coverage, financial audit, identity resolution, orphan financial universe, name-matching viability, core findings, recommended next step.

---

## 1. Executive Summary

- **Database:** SQLite, 170+ tables; core sources are `stg_payments`, `stg_appointments`, and `patients`. The main cleaned payment layer is `payments_clean` (876,054 rows); 59.6% linked to `patient_id`, 40.4% orphan. Of rows with non-zero `net_received`, 213,386 are orphan (39% of financially relevant rows).
- **Identity:** `patients` has no `record_no`; linkage is via `record_no_patient_map` (payment-derived, 10,228 rows), `patient_record_map` (phone-based, 41,158 rows), and `payments_recordno_patient_bridge_v3` (153,298 rows). Orphan financial rows all have `record_no`; total orphan net sum ≈ 440.65B (Rials).
- **Bottleneck:** Orphan financial volume (213,386 rows, 62,376 distinct `record_no`) with no direct `record_no` on `patients`; current maps cover a fraction of orphan `record_no`s. Name-only recovery is not viable (matches are ambiguous).
- **Recommended direction:** Prioritize strengthening the **record_no → patient_id** identity layer (appointment-side and payment-side) and then re-run payment linkage from that map; avoid further speculative recovery experiments until this is in place.

---

## 2. Table Inventory

**All tables (from `sqlite_master`):** 170+ tables. Classification below.

### Core source tables
- **stg_payments** — raw payment import (876,054 rows).
- **stg_appointments** — raw appointment import (1,015,442 rows).
- **patients** — patient master (140,531 rows); `id`, `name`, `phone`, `national_id`, `first_visit_date`; no `record_no`.

### Core cleaned / operational
- **payments_clean** — cleaned payments with `record_no`, `patient_id`, `net_received`, etc. (876,054 rows).
- **appointments** — canonical appointments with `patient_id`, `appointment_date`, etc. (446,437 rows).

### Mapping tables (record_no ↔ patient_id)
- **record_no_patient_map** — record_no → patient_id (payment-derived, direct_payment_patient_id); 10,228 rows.
- **patient_record_map** — record_no → patient_id (phone-based); 41,158 rows.
- **patient_recordno_map** — union/aggregate record_no ↔ patient_id (per-year variants: 1395–1404).
- **record_no_patient_map_enriched**, **record_no_patient_map_text_v3** — enriched/text variants of record_no mapping.

### Bridge tables
- **payments_recordno_patient_bridge_v3** — payment row → record_no token, name, phone, patient_id; 153,298 rows.
- **appointment_recordno_bridge** — appointment-side record_no + name/phone (from files); 342,158 rows.
- **bridge_1395_payment_appointment** … **bridge_1404_payment_appointment** — per-year payment–appointment bridges.
- **bridge_all_years**, **bridge_tier_d_candidates**, **bridge_tier_e_candidates**.
- **patient_mobile_norm_bridge**, **payments_phone_norm_bridge**, **national_id_layer_bridge_union**, etc.

### Derived / scoring tables
- **patient_financial_summary**, **patient_financial_profile**, **patient_lifetime_value**, **patient_value_score_v1/v2**, **patient_payment_fact_v1/v2**.
- **financial_patient_dim**, **patient_identifiers**, **patient_identity_evidence**, **patient_insurance_profile**.
- **payments_identity_clean_v2**, **payments_identity_clean_v3** — payment-side identity/name/record_no cleanup.

### Diagnostic / temporary
- **orphan_financial_names** — orphan payment record_no + extracted name; 62,376 rows.
- **unrecovered_***, **tmp_***, **zero_score_***, **unrecovered_identity_diagnostics**, **unrecovered_patient_diagnostics**.
- **identity_match_candidates**, **identity_match_decisions**, **identity_fuzzy_review_***, **recovery_run_metrics_v2**.

### Other (reference, config, national_id, etc.)
- **insurance_reference**, **insurance_reference_raw**, **doctor_dim**, **doctor_master**, **service_dim**, **schema_migrations**, **import_runs**.
- **national_id_*** (layer, bridge, profile, patient_side, etc.).
- **patient_phone_***, **payments_match_***, **appointment_match_***.

---

## 3. Key Schemas

### payments_clean
| # | Column           | Type    | Notes        |
|---|------------------|---------|--------------|
| 0 | payment_id       | TEXT    | PK           |
| 1 | stg_payment_id   | INTEGER |              |
| 2 | import_run_id    | TEXT    |              |
| 3 | file_name        | TEXT    |              |
| 4 | sheet_name       | TEXT    |              |
| 5 | row_number       | INTEGER |              |
| 6 | loaded_at        | TEXT    |              |
| 7 | record_no        | TEXT    | **Join key** |
| 8 | patient_id       | INTEGER | **Link**     |
| 9 | join_confidence  | REAL    |              |
|10 | patient_name_raw | TEXT    |              |
|…  | …                |         |              |
|21 | net_received     | REAL    | **Financial**|
|22 | parse_status     | TEXT    |              |

### patients
| # | Column          | Type        | Notes   |
|---|-----------------|-------------|---------|
| 0 | id              | INTEGER     | PK      |
| 1 | name            | VARCHAR(100)| NOT NULL|
| 2 | phone           | VARCHAR(20) | NOT NULL|
| 3 | national_id     | VARCHAR(20) |         |
| 4 | first_visit_date| DATETIME    | NOT NULL|
| 5 | created_at      | DATETIME    |         |
| 6 | updated_at      | DATETIME    |         |
| 7 | payment_type    | VARCHAR(20) |         |
| 8 | lifetime_value_score | REAL |     |

**No `record_no` column.** Linkage to payment `record_no` is only via mapping tables.

### record_no_patient_map
| # | Column      | Type  | Notes                    |
|---|-------------|-------|--------------------------|
| 0 | record_no   | TEXT  | PK / join key            |
| 1 | patient_id  | INTEGER |                         |
| 2 | phone_norm  | TEXT  |                          |
| 3 | match_method| TEXT  | e.g. direct_payment_patient_id |
| 4 | confidence  | REAL  |                          |
| 5 | evidence_count | INTEGER |                      |
| 6 | mapped_at   | TEXT  |                          |

### patient_record_map
| # | Column      | Type    | Notes   |
|---|-----------|---------|--------|
| 0 | record_no | TEXT    | PK     |
| 1 | patient_id| INTEGER |        |
| 2 | match_method | TEXT | e.g. phone |
| 3 | confidence| REAL    |        |
| 4 | created_at| TEXT    |        |
| 5 | updated_at| TEXT    |        |

### payments_recordno_patient_bridge_v3
| # | Column           | Type | Notes        |
|---|------------------|-----|--------------|
| 0 | payment_rowid    | INT | payment ref  |
| 1 | payment_name_raw | TEXT|              |
| 2 | payment_name_clean | TEXT|            |
| 3 | record_no_token  | TEXT| **Join key** |
| 4 | phone_norm       | TEXT|              |
| 5 | patient_id       | INT | **Link**     |

### orphan_financial_names
| # | Column          | Type | Notes            |
|---|-----------------|-----|------------------|
| 0 | record_no       | TEXT| orphan record_no  |
| 1 | patient_name_raw| TEXT| raw from payment  |
| 2 | extracted_name  | TEXT| normalized name   |

### appointments
| # | Column    | Type   | Notes     |
|---|----------|--------|-----------|
| 0 | id       | INTEGER| PK        |
| 1 | patient_id | INTEGER| **Link** |
| 2 | appointment_date | DATETIME |   |
| 3 | payment_type     | VARCHAR(12) |  |
| 4 | treatment_type   | VARCHAR(12) |  |
| 5 | priority_score   | FLOAT |        |
| … | …        |       |           |

No `record_no` column on `appointments`; appointment-side `record_no` lives in **appointment_recordno_bridge** (record_no, patient_name_raw, patient_name_norm, phone_raw, phone_norm, appointment_date_raw, appointment_year, evidence_type).

---

## 4. Row Count Summary

| Table                              | Row count  |
|------------------------------------|------------|
| payments_clean                     | 876,054    |
| patients                           | 140,531    |
| record_no_patient_map              | 10,228     |
| patient_record_map                 | 41,158     |
| payments_recordno_patient_bridge_v3| 153,298    |
| orphan_financial_names             | 62,376     |
| appointments                       | 446,437    |
| stg_appointments                   | 1,015,442  |
| stg_payments                       | 876,054    |
| appointment_recordno_bridge       | 342,158    |

---

## 5. Index Summary

Indexes exist for the main join columns:

- **payments_clean:** `idx_payments_clean_patient_id`, `idx_payments_clean_record_no`, `idx_payments_clean_stg_payment_id`, `idx_payments_clean_loaded_at`; PK on `payment_id`.
- **patients:** `idx_patients_name`, `idx_patients_phone`, `idx_patients_national_id`, etc.; no index on `record_no` (column does not exist).
- **record_no_patient_map:** `idx_record_no_patient_map_record_no`, `idx_rnpm_patient_id`, `idx_rnpm_recordno`; unique/covering on (record_no, …).
- **patient_record_map:** `idx_patient_record_map_patient_id`; unique/covering on (record_no, patient_id).
- **payments_recordno_patient_bridge_v3:** `idx_bridge_v3_payment_rowid`, `idx_prpbv3_patient`, `idx_prpbv3_recordno`.

Conclusion: Join columns used in recovery (payments_clean.patient_id, record_no, stg_payment_id; record_no_patient_map.record_no; patient_record_map.record_no; bridge v3 payment_rowid/recordno) are indexed. No index on “patients.record_no” because the column does not exist.

---

## 6. Payment Coverage Summary

| Metric                         | Value    |
|--------------------------------|----------|
| Total rows (payments_clean)    | 876,054  |
| Linked (patient_id IS NOT NULL)| 522,530  |
| Orphan (patient_id IS NULL)    | 353,524  |
| Rows with ABS(net_received) > 0| 547,435  |
| Orphan with ABS(net_received) > 0 | 213,386 |
| Linked with ABS(net_received) > 0 | 334,049 |

So: 59.6% of payments are linked; 40.4% orphan. Of financially non-zero rows, 39% are orphan (213,386).

---

## 7. Financial Audit Summary (payments_clean)

| Metric                    | Value     |
|---------------------------|-----------|
| Total rows                | 876,054   |
| net_received IS NULL      | 0         |
| net_received = 0          | 328,619   |
| net_received > 0         | 546,314   |
| net_received < 0         | 1,121     |
| ABS(net_received) > 0    | 547,435   |
| SUM(net_received)        | 2,087,779,737,461 |
| SUM(ABS(net_received))    | 2,103,745,659,255 |

(Values in Rials; nulls and zeros handled via COALESCE.)

---

## 8. Identity Resolution Audit

- **patients table:** Does **not** contain `record_no`. Linkage from payment/appointment `record_no` to `patients.id` is only via mapping/bridge tables.
- **record_no_patient_map:** 10,228 rows; 7,747 distinct `record_no`; 7,747 distinct `patient_id` (sample: 1:1). Represents **payment-derived** mapping: `record_no` from payments that already had or got `patient_id` (match_method e.g. `direct_payment_patient_id`).
- **patient_record_map:** 41,158 rows; 41,158 distinct `record_no`; 29,207 distinct `patient_id`. Represents **phone-based** mapping: same `record_no` can map to same or different patients across rows; built from appointment/payment phone normalization and matching to `patients.phone`.
- **payments_recordno_patient_bridge_v3:** 153,298 rows; links payment row (payment_rowid) to record_no_token, cleaned name, phone_norm, and patient_id; used to push patient_id back into payment-side identity.

So:
- **record_no_patient_map** = payment-derived, high-confidence record_no → patient_id.
- **patient_record_map** = phone-based record_no → patient_id (more rows, more coverage, possible many-to-one/many-to-many by record_no).
- **Bridge v3** = payment-level bridge from payment row to patient_id using record_no/name/phone.

---

## 9. Orphan Financial Universe

- **Orphan financial rows** (patient_id IS NULL AND ABS(net_received) > 0): **213,386**.
- **Distinct orphan financial record_no:** **62,376** (from separate count on payments_clean; matches orphan_financial_names row count).
- **All orphan financial rows have record_no:** Yes; no rows with NULL/empty record_no in the orphan financial set (0 missing).
- **Amount band distribution (orphan, ABS(net_received)):**

| Band     | Count  |
|----------|--------|
| <1k      | 3      |
| 1k–10k   | 102    |
| 10k–100k | 22,659 |
| 100k–1M  | 114,942|
| ≥1M      | 75,680 |

- **Total net sum of orphan financial rows:** 440,654,249,363 (Rials).

---

## 10. Name Matching Viability

- **orphan_financial_names:** 62,376 rows; 55,849 distinct `extracted_name`.
- **Orphan record_nos with at least one exact name match to patients.name:** 673 (EXISTS subquery).
- **Unique vs ambiguous:** Among extracted_name that match at least one patient, **0** names match exactly one patient; **466** names match multiple patients (sample: e.g. 4, 4, 28 patients per name). So matches are **ambiguous**.
- **Conclusion:** Name-only recovery is **not viable** for safe 1:1 linking; name matches are overwhelmingly ambiguous. Use name only as a disambiguating signal (e.g. with record_no or phone), not as sole key.

---

## 11. Core Findings

1. **Main bottleneck:** Large orphan financial set (213,386 rows, 62,376 distinct record_no) with no direct way to resolve record_no to patient_id on the **patients** table. Existing maps (record_no_patient_map, patient_record_map, bridge v3) cover only a subset of these record_nos; the rest have no reliable identity path without a stronger record_no → patient_id layer.

2. **Trustworthy tables:** **stg_payments**, **stg_appointments**, **patients** (as master), **payments_clean** (as the canonical payment table with record_no, patient_id, net_received). **record_no_patient_map** and **patient_record_map** are trustworthy for the record_nos they contain; coverage is limited.

3. **Derived and limited:** **payments_recordno_patient_bridge_v3**, **orphan_financial_names**, **payments_identity_clean_v2/v3**, **appointment_recordno_bridge** — all derived from pipelines; useful but not sufficient for full orphan resolution. **patient_record_map** is larger but phone-based and can be many-to-one.

4. **Phone-based recovery:** **Moderately strong path** where phone is present and normalizable (patient_record_map has 41K rows and is used in bridges). It is **not** sufficient alone for the full orphan set because many orphan payments may lack usable phone or may collide.

5. **Name-based recovery:** **Not viable** as sole key; name matches are ambiguous (466 names match multiple patients; 0 unique in sampled classification). Name can support disambiguation only in combination with record_no or phone.

6. **record_no as identity key for orphan financial rows:** **Yes.** Every orphan financial row has a non-null record_no; record_no is the natural key to attach payments to identity. The gap is that **patients** does not have record_no and the current maps do not cover all 62,376 distinct orphan record_nos.

7. **Does patients support record_no-based direct matching?** **No.** The patients table has no record_no column. Direct matching is only via record_no_patient_map, patient_record_map, or bridge tables that themselves were built from payment/appointment record_no and phone/name logic.

---

## 12. Recommended Next Step

1. **Build or extend a single, authoritative record_no → patient_id map** that incorporates:
   - Appointment-side linkage: use **appointment_recordno_bridge** (record_no + name/phone) joined to **appointments** (patient_id) where possible (e.g. via matching name/phone to patients), and write (record_no, patient_id) into a consolidated map.
   - Payment-derived and phone-derived links already in **record_no_patient_map** and **patient_record_map**, with clear rules for conflict (e.g. prefer 1:1, then by confidence).
   - Goal: maximize distinct orphan record_nos that get a unique patient_id.

2. **Re-run payment linkage** from that map: update **payments_clean.patient_id** (and join_confidence) for rows where payments_clean.record_no is in the new map and currently patient_id IS NULL, using a single deterministic rule (e.g. one patient_id per record_no).

3. **Re-measure coverage:** After (1)–(2), recompute orphan count (patient_id IS NULL AND ABS(net_received) > 0), distinct orphan record_no count, and total orphan net sum; then decide if a further round (e.g. shadow identity layer or manual review for remaining record_nos) is justified.

Do **not** add more speculative recovery experiments (new scripts, many small tables) until this record_no–patient_id layer and one linkage pass are in place and measured.
