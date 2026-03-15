-- Patient priority profile: raw inputs for scoring (scores/tiers computed in Python).
-- Joins: master_patient_profile_v2, patient_insurance_profile_v2, payments_unified_staging.
-- Does not modify staging. Use financial/recovery DB (same as reception).

DROP VIEW IF EXISTS patient_priority_profile_v1;
CREATE VIEW patient_priority_profile_v1 AS
SELECT
  m.patient_id,
  m.crm_patient_code AS record_no,
  m.crm_patient_code,
  m.patient_name_canonical AS patient_name,
  COALESCE(i.most_recent_insurer, i.most_frequent_insurer) AS insurance_name,
  m.payment_rows_count AS visit_count,
  m.first_year AS first_visit_year,
  CASE
    WHEN m.first_year IS NOT NULL AND m.last_year IS NOT NULL AND m.last_year >= m.first_year
    THEN m.last_year - m.first_year + 1
    ELSE 0
  END AS relationship_years,
  m.payment_rows_count AS payment_count,
  m.total_net_received AS lifetime_net_received,
  m.positive_net_received_sum,
  m.negative_net_received_sum,
  COALESCE(i.distinct_insurers_count, 0) AS insurance_variants_count,
  (
    SELECT MAX(p.appointment_date_raw)
    FROM payments_unified_staging p
    WHERE p.record_no = m.crm_patient_code
      AND TRIM(COALESCE(p.appointment_date_raw, '')) <> ''
  ) AS last_payment_date,
  m.first_year,
  m.last_year
FROM master_patient_profile_v2 m
LEFT JOIN patient_insurance_profile_v2 i ON i.crm_patient_code = m.crm_patient_code;
