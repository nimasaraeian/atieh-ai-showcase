-- Resolved view: patients + record_no (from appointment bridge) + financial summary
DROP VIEW IF EXISTS v_patients_financial_resolved;
CREATE VIEW v_patients_financial_resolved AS
SELECT
  p.id AS patient_id,
  p.name AS patient_name,
  p.phone AS patient_phone,
  prm.record_no AS record_no,
  prm.match_method AS match_method,
  prm.confidence AS confidence,
  COALESCE(pfs.lifetime_net_received, 0) AS financial_value,
  COALESCE(pfs.lifetime_txn_count, 0) AS payment_rows,
  COALESCE(pfs.financial_value_score, 0) AS financial_value_score
FROM patients p
LEFT JOIN patient_recordno_map prm ON prm.patient_id = p.id
LEFT JOIN patient_financial_summary pfs ON pfs.record_no = prm.record_no;
