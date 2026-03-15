-- Patient insurance aggregation view from payments_unified_staging.insurer_raw.
-- Read-only: does not modify staging. One row per crm_patient_code (record_no).
-- SQLite: MAX_BY/MODE emulated via correlated subqueries.

DROP VIEW IF EXISTS patient_insurance_profile_v2;
CREATE VIEW patient_insurance_profile_v2 AS
SELECT
  p.record_no AS crm_patient_code,
  (SELECT p2.insurer_raw
   FROM payments_unified_staging p2
   WHERE p2.record_no = p.record_no
     AND p2.insurer_raw IS NOT NULL AND TRIM(p2.insurer_raw) <> ''
   ORDER BY p2.shamsi_year DESC, p2.id DESC
   LIMIT 1) AS most_recent_insurer,
  (SELECT p2.insurer_raw
   FROM payments_unified_staging p2
   WHERE p2.record_no = p.record_no
     AND p2.insurer_raw IS NOT NULL AND TRIM(p2.insurer_raw) <> ''
   GROUP BY p2.insurer_raw
   ORDER BY COUNT(*) DESC
   LIMIT 1) AS most_frequent_insurer,
  COUNT(DISTINCT p.insurer_raw) AS distinct_insurers_count,
  COUNT(*) AS payment_rows_count
FROM payments_unified_staging p
WHERE p.record_no IS NOT NULL AND TRIM(p.record_no) <> ''
  AND p.insurer_raw IS NOT NULL AND TRIM(p.insurer_raw) <> ''
GROUP BY p.record_no;
