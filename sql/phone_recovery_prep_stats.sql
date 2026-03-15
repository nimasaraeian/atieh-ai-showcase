-- Verification: Phone Recovery Preparation stats
-- Run after scripts/phone_recovery_prep.py

SELECT (SELECT COUNT(*) FROM payments_unified_staging) AS total_staging_rows;
SELECT (SELECT COUNT(*) FROM payments_phone_normalized WHERE is_valid = 1) AS valid_normalized_payment_phones;
SELECT (SELECT COUNT(*) FROM patients_phone_normalized WHERE is_valid = 1) AS valid_normalized_patient_phones;
SELECT (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'single') AS single_matches;
SELECT (SELECT COUNT(DISTINCT patient_id) FROM payments_phone_patient_match WHERE match_status = 'single' AND patient_id IS NOT NULL) AS unique_patients_matched;
SELECT (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'collision') AS collisions;
SELECT (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'no_match') AS no_match;
SELECT (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'single') AS coverage_gained_by_phone;

SELECT
  (SELECT COUNT(*) FROM payments_unified_staging) AS total_staging_rows,
  (SELECT COUNT(*) FROM payments_phone_normalized WHERE is_valid = 1) AS valid_payment_phones,
  (SELECT COUNT(*) FROM patients_phone_normalized WHERE is_valid = 1) AS valid_patient_phones,
  (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'single') AS single_matches,
  (SELECT COUNT(DISTINCT patient_id) FROM payments_phone_patient_match WHERE match_status = 'single') AS unique_patients_matched,
  (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'collision') AS collisions,
  (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'no_match') AS no_match,
  (SELECT COUNT(*) FROM payments_phone_patient_match WHERE match_status = 'single') AS coverage_gained_by_phone;
