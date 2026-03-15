# Master Patient Profile V2 Report

Payments-first master identity architecture. Built from payment_identity_master, patient_master_link_v2, and patients_identity_normalized.

**Generated:** 2026-03-15T15:44:59.841698

## 1. Distinct payment identity entities

| Metric | Value |
|--------|-------|
| payment_identity_master (distinct financial identities) | 128,266 |
| Linked to a patient (patient_master_link_v2) | 49,852 |
| Unlinked (identity only, no patient) | 78,414 |

## 2. Distinct patients linked & patient coverage %

| Metric | Value |
|--------|-------|
| Distinct patient_id in master_patient_profile_v2 | 37,340 |
| Total patients (patients_identity_normalized) | 140,531 |
| **Patient coverage %** | 26.57% |

## 3. Payment row coverage %

| Metric | Value |
|--------|-------|
| Payment rows covered (sum of payment_rows_count in v2) | 615,515 |
| Total payment rows with extracted code (denominator) | 876,054 |
| **Payment row coverage %** | 70.26% |

## 4. Share of deterministic Tier A / Tier B links

| link_tier | Count | % of linked |
|-----------|-------|-------------|
| A | 49,852 | 100.0% |
| B | 0 | 0.0% |
| C | 0 | 0.0% |
| D | 0 | 0.0% |
| **A+B (deterministic)** | **49,852** | **100.0%** |

## 5. Review queue size

| Metric | Value |
|--------|-------|
| Rows with review_flag=1 | 17,257 |
| % of master_patient_profile_v2 | 34.6% |

### Review reason breakdown

| review_reason | Count |
|---------------|-------|
| multiple_candidates_same_tier | 17,257 |

## 6. Identity strength (payment side)

| identity_strength_tier | Count |
|------------------------|-------|
| medium | 9,426 |
| strong | 40,170 |
| weak | 256 |

## 7. Does coverage move far beyond 20%?

**Yes – coverage moves far beyond 20%.**

---

## Run order (from repo root)

1. Schema: `sqlite3 atieh_clinic_recovery81_test.db < sql/identity_resolution/014_payment_identity_master_v2_schema.sql`
2. Payment identity master: `python scripts/build_payment_identity_master_v2.py`
3. Patient links: `python scripts/build_patient_master_link_v2.py`
4. Profile v2: `python scripts/build_master_patient_profile_v2.py`
5. This report: `python scripts/master_patient_profile_v2_stats.py`

## Sample query patterns for backend/API

Search by CRM code: `SELECT * FROM master_patient_profile_v2 WHERE crm_patient_code = ?`

Search by patient name_key: `SELECT * FROM master_patient_profile_v2 WHERE patient_name_key = ?`

Search by phone: `SELECT * FROM master_patient_profile_v2 WHERE primary_phone = ?`

Fetch by patient_id: `SELECT * FROM master_patient_profile_v2 WHERE patient_id = ?`

Only high-confidence (no review): `SELECT * FROM master_patient_profile_v2 WHERE review_flag = 0`

## Validation queries (SQLite)

```sql
SELECT COUNT(*) AS payment_identity_entities FROM payment_identity_master;
SELECT COUNT(DISTINCT patient_id) AS distinct_patients FROM master_patient_profile_v2;
SELECT SUM(payment_rows_count) AS payment_rows_covered FROM master_patient_profile_v2;
SELECT link_tier, COUNT(*) FROM master_patient_profile_v2 GROUP BY link_tier;
SELECT COUNT(*) AS review_count FROM patient_master_link_v2 WHERE review_flag = 1;
```
