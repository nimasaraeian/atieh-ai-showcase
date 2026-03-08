-- نمای بیماران با وضعیت مالی (منطبق با payments_clean)
-- بیمارانی که حداقل یک پرداخت به آن‌ها لینک شده
DROP VIEW IF EXISTS v_patients_with_financial;
CREATE VIEW v_patients_with_financial AS
SELECT
  p.id AS patient_id,
  p.name AS patient_name,
  p.phone AS patient_phone,
  1 AS has_financial,
  COALESCE(SUM(pc.net_received), 0) AS total_net_received,
  COUNT(pc.payment_id) AS payment_count
FROM patients p
JOIN payments_clean pc ON pc.patient_id = p.id
WHERE pc.patient_id IS NOT NULL
GROUP BY p.id, p.name, p.phone;
