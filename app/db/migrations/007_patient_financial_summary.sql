PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS patient_financial_summary (
  record_no TEXT PRIMARY KEY,

  -- lifetime aggregates
  lifetime_txn_count INTEGER NOT NULL DEFAULT 0,
  lifetime_net_received REAL NOT NULL DEFAULT 0,
  lifetime_patient_paid REAL NOT NULL DEFAULT 0,
  lifetime_insurer_paid REAL NOT NULL DEFAULT 0,

  -- negatives / adjustments
  lifetime_negative_net REAL NOT NULL DEFAULT 0,
  lifetime_negative_txn_count INTEGER NOT NULL DEFAULT 0,

  -- recency / time
  first_payment_date_raw TEXT,
  last_payment_date_raw TEXT,

  -- payer mix
  cash_txn_count INTEGER NOT NULL DEFAULT 0,
  insurance_txn_count INTEGER NOT NULL DEFAULT 0,

  -- recent windows (based on loaded_at ordering proxy)
  recent_txn_count INTEGER NOT NULL DEFAULT 0,
  recent_net_received REAL NOT NULL DEFAULT 0,

  -- score 0..1 for engine + reporting
  financial_value_score REAL NOT NULL DEFAULT 0,

  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pfs_score ON patient_financial_summary(financial_value_score);