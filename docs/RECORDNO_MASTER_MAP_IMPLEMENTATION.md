# Implementation Plan: Authoritative record_no → patient_id Master Map

**Database:** atieh_clinic_recovery81_test.db  
**Goal:** Build a single conflict-aware, evidence-based master mapping table and use it to relink orphan rows in `payments_clean` only.

---

## 1. Design

### 1.1 Sources (in priority order)

| Priority | Source table | Candidate table | Origin |
|---------|--------------|-----------------|--------|
| 1 | record_no_patient_map | recordno_candidate_from_payments | Payment-derived; direct payment → patient_id linkage. |
| 2 | patient_record_map | recordno_candidate_from_phone | Phone-based; record_no ↔ patient_id from phone normalization. |
| 3 | appointment_recordno_bridge + stg_appointments | recordno_candidate_from_appointments | Appointment file row → patient_id via (source_file, source_sheet, source_row). Only rows where `record_no` is **numeric** (4–10 digits) are used; in this DB many bridge rows have name in `record_no` for xlsx sources, so this candidate set may be small or empty. |

### 1.2 Output tables

- **recordno_candidate_from_payments** — One row per (record_no, patient_id) from `record_no_patient_map`; source = 'payments'.
- **recordno_candidate_from_phone** — One row per (record_no, patient_id) from `patient_record_map`; source = 'phone'.
- **recordno_candidate_from_appointments** — One row per (record_no, patient_id) from bridge + stg_appointments; source = 'appointments'. Only numeric `record_no`.
- **recordno_ambiguous** — record_no values that appear with more than one distinct patient_id in the union of candidates (excluded from master).
- **recordno_patient_master_map** — Final 1:1 mapping: (record_no, patient_id, winning_source). Only record_nos that are unique across all sources and pass conflict rules.
- **orphan_payment_relink_candidates** — Orphan payment rows (payment_id, record_no, patient_id) that can be relinked using the master map.
- **payments_clean** — Updated only for current orphans: set `patient_id` (and optionally `join_confidence`) where relink is applied.

### 1.3 Flow

1. Inspect appointment-side columns (bridge + stg_appointments).
2. Create and fill the three candidate tables; normalize record_no (trim, non-empty).
3. Detect ambiguous record_nos (multiple patient_ids in union); store in recordno_ambiguous.
4. Build recordno_patient_master_map with explicit source priority and conflict rules (payments > phone > appointments; no mixing for same record_no).
5. Build orphan_payment_relink_candidates from payments_clean LEFT JOIN master map where patient_id IS NULL.
6. Update payments_clean.patient_id only for orphans that appear in relink candidates.
7. Re-measure coverage before/after.

---

## 2. Conflict Rules

- **Uniqueness:** A record_no is included in the master map only if it maps to exactly one patient_id in the **final** candidate union after source priority is applied.
- **Source priority (for assigning winning_source):**  
  1) payments (record_no_patient_map),  
  2) phone (patient_record_map),  
  3) appointments (bridge + stg).  
  If the same record_no appears in multiple sources with the **same** patient_id, the highest-priority source wins. If it appears with **different** patient_ids, that record_no is **ambiguous** and excluded from the master map.
- **Exclusion:** Any record_no that has more than one distinct patient_id in the union of all candidates is written to recordno_ambiguous and must not appear in recordno_patient_master_map.
- **No name-only, no fuzzy:** Only existing tables and exact joins; no name matching and no speculative logic.

---

## 3. SQL Build Steps

### Phase 0: Inspection (appointment-side)

Run once to confirm join columns and numeric record_no availability:

```sql
-- 0.1 Columns for join: bridge → stg_appointments
--    bridge: source_file, source_sheet, source_row, record_no
--    stg_appointments: file_name, sheet_name, row_number, patient_id
SELECT 'bridge' AS tbl, source_file, source_sheet, source_row, record_no
FROM appointment_recordno_bridge WHERE source_file LIKE '%.xlsx' LIMIT 3;
SELECT 'stg_appointments' AS tbl, file_name, sheet_name, row_number, patient_id
FROM stg_appointments WHERE file_name LIKE '%.xlsx' LIMIT 3;

-- 0.2 Optional: index to speed bridge ↔ stg join (run before Phase 1 if needed)
-- CREATE INDEX IF NOT EXISTS idx_stg_appointments_file_sheet_row ON stg_appointments(file_name, sheet_name, row_number);
```

### Phase 1: Create candidate tables (per source)

```sql
-- 1.1 recordno_candidate_from_payments
DROP TABLE IF EXISTS recordno_candidate_from_payments;
CREATE TABLE recordno_candidate_from_payments (
    record_no    TEXT NOT NULL,
    patient_id   INTEGER NOT NULL,
    source       TEXT NOT NULL DEFAULT 'payments',
    PRIMARY KEY (record_no)
);
INSERT OR REPLACE INTO recordno_candidate_from_payments (record_no, patient_id, source)
SELECT TRIM(record_no), patient_id, 'payments'
FROM record_no_patient_map
WHERE record_no IS NOT NULL AND TRIM(record_no) <> '';

-- 1.2 recordno_candidate_from_phone
DROP TABLE IF EXISTS recordno_candidate_from_phone;
CREATE TABLE recordno_candidate_from_phone (
    record_no    TEXT NOT NULL,
    patient_id   INTEGER NOT NULL,
    source       TEXT NOT NULL DEFAULT 'phone',
    PRIMARY KEY (record_no)
);
INSERT OR REPLACE INTO recordno_candidate_from_phone (record_no, patient_id, source)
SELECT TRIM(record_no), patient_id, 'phone'
FROM patient_record_map
WHERE record_no IS NOT NULL AND TRIM(record_no) <> '' AND patient_id IS NOT NULL;

-- 1.3 recordno_candidate_from_appointments
--    Join: appointment_recordno_bridge (source_file, source_sheet, source_row) = stg_appointments (file_name, sheet_name, row_number)
--    Only numeric record_no: 4–10 digits. No PK(record_no) so multiple (record_no, patient_id) pairs are kept for ambiguity detection.
DROP TABLE IF EXISTS recordno_candidate_from_appointments;
CREATE TABLE recordno_candidate_from_appointments (
    record_no    TEXT NOT NULL,
    patient_id   INTEGER NOT NULL,
    source       TEXT NOT NULL DEFAULT 'appointments'
);
INSERT INTO recordno_candidate_from_appointments (record_no, patient_id, source)
SELECT DISTINCT TRIM(arb.record_no), stg.patient_id, 'appointments'
FROM appointment_recordno_bridge arb
INNER JOIN stg_appointments stg
  ON stg.file_name = arb.source_file
  AND (stg.sheet_name = arb.source_sheet OR (stg.sheet_name IS NULL AND arb.source_sheet IS NULL))
  AND stg.row_number = arb.source_row
WHERE arb.record_no IS NOT NULL
  AND TRIM(arb.record_no) <> ''
  AND stg.patient_id IS NOT NULL
  AND TRIM(arb.record_no) GLOB '[0-9][0-9][0-9][0-9]*'
  AND LENGTH(TRIM(arb.record_no)) BETWEEN 4 AND 10;
```

*Note:* In this DB, appointment_recordno_bridge often has non-numeric `record_no` for xlsx-sourced rows (patient names). The filter above keeps only 4–10 digit record_nos; the appointment candidate table may be empty or small. No name-only matching is used.

### Phase 2: Detect ambiguous record_nos

```sql
-- 2.1 Single table of all (record_no, patient_id) with source
DROP TABLE IF EXISTS recordno_candidate_union;
CREATE TABLE recordno_candidate_union (
    record_no   TEXT NOT NULL,
    patient_id  INTEGER NOT NULL,
    source      TEXT NOT NULL
);
INSERT INTO recordno_candidate_union (record_no, patient_id, source)
SELECT record_no, patient_id, source FROM recordno_candidate_from_payments
UNION ALL
SELECT record_no, patient_id, source FROM recordno_candidate_from_phone
UNION ALL
SELECT record_no, patient_id, source FROM recordno_candidate_from_appointments;

-- 2.2 Ambiguous: record_nos with more than one distinct patient_id
DROP TABLE IF EXISTS recordno_ambiguous;
CREATE TABLE recordno_ambiguous (record_no TEXT PRIMARY KEY);
INSERT OR REPLACE INTO recordno_ambiguous (record_no)
SELECT record_no
FROM recordno_candidate_union
GROUP BY record_no
HAVING COUNT(DISTINCT patient_id) > 1;
```

### Phase 3: Build master map (unique only; source priority)

```sql
-- 3.1 For each record_no we want one patient_id. Priority: payments > phone > appointments.
--    First take all from payments; then fill from phone where record_no not yet in master; then from appointments.
DROP TABLE IF EXISTS recordno_patient_master_map;
CREATE TABLE recordno_patient_master_map (
    record_no       TEXT NOT NULL PRIMARY KEY,
    patient_id      INTEGER NOT NULL,
    winning_source  TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Payments (priority 1)
INSERT OR IGNORE INTO recordno_patient_master_map (record_no, patient_id, winning_source)
SELECT record_no, patient_id, 'payments'
FROM recordno_candidate_from_payments
WHERE record_no NOT IN (SELECT record_no FROM recordno_ambiguous);

-- Phone (priority 2): only where not already in master
INSERT OR IGNORE INTO recordno_patient_master_map (record_no, patient_id, winning_source)
SELECT record_no, patient_id, 'phone'
FROM recordno_candidate_from_phone
WHERE record_no NOT IN (SELECT record_no FROM recordno_ambiguous)
  AND record_no NOT IN (SELECT record_no FROM recordno_patient_master_map);

-- Appointments (priority 3): only where not already in master
INSERT OR IGNORE INTO recordno_patient_master_map (record_no, patient_id, winning_source)
SELECT record_no, patient_id, 'appointments'
FROM recordno_candidate_from_appointments
WHERE record_no NOT IN (SELECT record_no FROM recordno_ambiguous)
  AND record_no NOT IN (SELECT record_no FROM recordno_patient_master_map);
```

### Phase 4: Row counts and quality metrics

```sql
-- 4.1 Candidate counts
SELECT 'recordno_candidate_from_payments'    AS tbl, COUNT(*) AS cnt FROM recordno_candidate_from_payments
UNION ALL
SELECT 'recordno_candidate_from_phone',       COUNT(*) FROM recordno_candidate_from_phone
UNION ALL
SELECT 'recordno_candidate_from_appointments', COUNT(*) FROM recordno_candidate_from_appointments
UNION ALL
SELECT 'recordno_ambiguous',                  COUNT(*) FROM recordno_ambiguous
UNION ALL
SELECT 'recordno_patient_master_map',         COUNT(*) FROM recordno_patient_master_map;
```

### Phase 5: Orphan relink candidates and inject table

```sql
-- 5.1 Orphan payment rows that have a record_no in the master map
DROP TABLE IF EXISTS orphan_payment_relink_candidates;
CREATE TABLE orphan_payment_relink_candidates (
    payment_id   TEXT NOT NULL,
    record_no    TEXT NOT NULL,
    patient_id   INTEGER NOT NULL,
    winning_source TEXT NOT NULL,
    PRIMARY KEY (payment_id)
);
INSERT OR REPLACE INTO orphan_payment_relink_candidates (payment_id, record_no, patient_id, winning_source)
SELECT p.payment_id, p.record_no, m.patient_id, m.winning_source
FROM payments_clean p
INNER JOIN recordno_patient_master_map m ON m.record_no = TRIM(p.record_no)
WHERE p.patient_id IS NULL
  AND p.record_no IS NOT NULL
  AND TRIM(p.record_no) <> '';
```

### Phase 6: Update payments_clean (orphans only)

```sql
-- 6.1 Backup current orphan count / sum before update (run verification first).
-- 6.2 Update payments_clean only for rows that are current orphans and in relink candidates.
UPDATE payments_clean
SET patient_id = (
    SELECT r.patient_id
    FROM orphan_payment_relink_candidates r
    WHERE r.payment_id = payments_clean.payment_id
),
join_confidence = 0.95
WHERE patient_id IS NULL
  AND payment_id IN (SELECT payment_id FROM orphan_payment_relink_candidates);
```

### Phase 7: Re-measure coverage (run after update)

Use verification queries below.

---

## 4. Verification Queries

### Before update (after Phase 5)

```sql
-- Orphan counts
SELECT COUNT(*) AS orphan_rows FROM payments_clean WHERE patient_id IS NULL;
SELECT COUNT(*) AS orphan_with_net FROM payments_clean WHERE patient_id IS NULL AND ABS(COALESCE(net_received,0)) > 0;
SELECT COUNT(DISTINCT record_no) AS distinct_orphan_record_no FROM payments_clean WHERE patient_id IS NULL AND record_no IS NOT NULL AND TRIM(record_no) <> '';

-- Relink candidate stats
SELECT COUNT(*) AS relink_candidate_rows FROM orphan_payment_relink_candidates;
SELECT COUNT(DISTINCT record_no) AS distinct_record_no_in_relink FROM orphan_payment_relink_candidates;
```

### After update (after Phase 6)

```sql
-- Orphan counts (should decrease)
SELECT COUNT(*) AS orphan_rows FROM payments_clean WHERE patient_id IS NULL;
SELECT COUNT(*) AS orphan_with_net FROM payments_clean WHERE patient_id IS NULL AND ABS(COALESCE(net_received,0)) > 0;
SELECT COUNT(DISTINCT record_no) AS distinct_orphan_record_no FROM payments_clean WHERE patient_id IS NULL AND record_no IS NOT NULL AND TRIM(record_no) <> '';

-- Linked counts (should increase)
SELECT COUNT(*) AS linked_rows FROM payments_clean WHERE patient_id IS NOT NULL;
SELECT COUNT(*) AS linked_with_net FROM payments_clean WHERE patient_id IS NOT NULL AND ABS(COALESCE(net_received,0)) > 0;
```

### Master map and quality

```sql
SELECT winning_source, COUNT(*) AS cnt FROM recordno_patient_master_map GROUP BY winning_source;
SELECT COUNT(*) AS ambiguous_excluded FROM recordno_ambiguous;
```

---

## 5. Expected Outcome

- **recordno_patient_master_map** contains only record_nos that map to exactly one patient_id, with a single winning source (payments, phone, or appointments). All ambiguous record_nos are in **recordno_ambiguous** and are not used for relink.
- **orphan_payment_relink_candidates** contains one row per orphan payment that can be relinked; **payments_clean** is updated only for those rows (patient_id and join_confidence set).
- **Coverage:** Orphan count and orphan-with-non-zero-net count decrease by the number of relinked rows; linked count increases by the same. No name-only or fuzzy logic; changes are audit-friendly and reversible (you can store pre-update patient_id in a backup column if desired).
