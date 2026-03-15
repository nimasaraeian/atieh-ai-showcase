-- Verification queries: National ID Recovery Preparation stats
-- Run after scripts/unified_payments_import.py and scripts/national_id_recovery_prep.py

-- 1) Total staging rows
SELECT COUNT(*) AS total_staging_rows FROM payments_unified_staging;

-- 2) Valid national_id (10-digit normalized)
SELECT COUNT(*) AS valid_national_id_count
FROM payments_national_id_normalized
WHERE is_valid = 1 AND national_id_norm IS NOT NULL AND LENGTH(national_id_norm) = 10;

-- 3) Match with patients (single)
SELECT COUNT(*) AS match_with_patients_single
FROM payments_national_id_patient_match
WHERE match_status = 'single';

-- 4) Unique patients matched
SELECT COUNT(DISTINCT patient_id) AS unique_patient_match
FROM payments_national_id_patient_match
WHERE match_status = 'single' AND patient_id IS NOT NULL;

-- 5) Collision (one nid → multiple patients)
SELECT COUNT(*) AS collision_count
FROM payments_national_id_patient_match
WHERE match_status = 'collision';

-- 6) No match
SELECT COUNT(*) AS no_match_count
FROM payments_national_id_patient_match
WHERE match_status = 'no_match';

-- 7) Coverage gained by national_id (rows that would get a patient_id from NID)
SELECT COUNT(*) AS coverage_gained_by_national_id
FROM payments_national_id_patient_match
WHERE match_status = 'single';

-- All-in-one summary
SELECT
  (SELECT COUNT(*) FROM payments_unified_staging) AS total_staging_rows,
  (SELECT COUNT(*) FROM payments_national_id_normalized WHERE is_valid = 1) AS valid_national_id,
  (SELECT COUNT(*) FROM payments_national_id_patient_match WHERE match_status = 'single') AS match_single,
  (SELECT COUNT(DISTINCT patient_id) FROM payments_national_id_patient_match WHERE match_status = 'single') AS unique_patient_match,
  (SELECT COUNT(*) FROM payments_national_id_patient_match WHERE match_status = 'collision') AS collision_count,
  (SELECT COUNT(*) FROM payments_national_id_patient_match WHERE match_status = 'no_match') AS no_match_count;
