-- 018_insurance_priority_rank.sql
-- Insurance priority based on payment speed from reference Excel (تاریخ پرداختی بیمه ها.xlsx).
-- Populated by scripts/populate_insurance_priority_from_excel.py

CREATE TABLE IF NOT EXISTS insurance_priority_rank (
  insurance_name      TEXT PRIMARY KEY,
  payment_speed_group TEXT,
  priority_score      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_insurance_priority_rank_score
  ON insurance_priority_rank(priority_score DESC);
