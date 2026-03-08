CREATE VIEW IF NOT EXISTS v_financial_for_engine AS
SELECT
  prm.patient_id,
  pfs.record_no,
  pfs.financial_value_score,
  pfs.lifetime_net_received,
  pfs.lifetime_txn_count,
  pfs.recent_net_received,
  pfs.recent_txn_count,
  pfs.last_payment_date_raw
FROM patient_record_map prm
JOIN patient_financial_summary pfs
  ON pfs.record_no = prm.record_no;