-- Canonical receptionist search: patient_recordno_map + record_no_patient_map as PRIMARY source.
-- These tables have real record_no, patient_name_norm, phone_norm (no UNKNOWN, no null placeholders).
-- Financial fields joined from patient_financial_summary / financial_identity_profile when available.
DROP VIEW IF EXISTS v_receptionist_search;
CREATE VIEW v_receptionist_search AS
SELECT
  prm.record_no,
  prm.patient_name_norm AS patient_name,
  prm.phone_norm AS mobile,
  pfs.financial_tier,
  pfs.lifetime_net_received,
  pfs.last_payment_date_raw,
  CASE
    WHEN prm.phone_norm IS NOT NULL AND prm.phone_norm <> '' AND prm.phone_norm NOT LIKE 'UNKNOWN%'
    THEN 1
    ELSE 0
  END AS has_real_mobile
FROM patient_recordno_map prm
LEFT JOIN (
  SELECT record_no, financial_tier, lifetime_net_received, last_payment_date_raw
  FROM financial_identity_profile
) pfs ON pfs.record_no = prm.record_no
WHERE prm.record_no IS NOT NULL
  AND TRIM(prm.record_no) <> ''
  AND prm.record_no <> '-'
  AND prm.record_no GLOB '[0-9]*'

UNION ALL

SELECT
  rnpm.record_no,
  COALESCE(p.name, '') AS patient_name,
  rnpm.phone_norm AS mobile,
  NULL AS financial_tier,
  NULL AS lifetime_net_received,
  NULL AS last_payment_date_raw,
  CASE
    WHEN rnpm.phone_norm IS NOT NULL AND rnpm.phone_norm <> '' AND rnpm.phone_norm NOT LIKE 'UNKNOWN%'
    THEN 1
    ELSE 0
  END AS has_real_mobile
FROM record_no_patient_map rnpm
LEFT JOIN patients p ON p.id = rnpm.patient_id
WHERE rnpm.patient_id IS NOT NULL
  AND rnpm.record_no IS NOT NULL
  AND TRIM(rnpm.record_no) <> ''
  AND rnpm.record_no <> '-'
  AND rnpm.record_no GLOB '[0-9]*'
  AND NOT EXISTS (SELECT 1 FROM patient_recordno_map prm2 WHERE prm2.record_no = rnpm.record_no);
