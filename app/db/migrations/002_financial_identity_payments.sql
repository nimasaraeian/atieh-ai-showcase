-- 002_financial_identity_payments.sql

PRAGMA foreign_keys=ON;

-- 1) Identity map for patients (enterprise approach)
CREATE TABLE IF NOT EXISTS patient_identifiers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  id_type TEXT NOT NULL,              -- 'record_no' | 'phone' | 'national_id'
  id_value TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 1.0,
  source TEXT,                        -- 'stg_payments' | 'patients' | 'manual'
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(id_type, id_value),
  FOREIGN KEY(patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_patient_identifiers_patient_id ON patient_identifiers(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_identifiers_type_value ON patient_identifiers(id_type, id_value);

-- 2) Canonical clean payments table
CREATE TABLE IF NOT EXISTS payments_clean (
  payment_id TEXT PRIMARY KEY,        -- deterministic unique id
  stg_payment_id INTEGER,             -- stg_payments.id
  import_run_id TEXT,
  file_name TEXT,
  sheet_name TEXT,
  row_number INTEGER,
  loaded_at TEXT,

  -- core fields
  record_no TEXT,                     -- extracted from patient_name_raw or row_json
  patient_id INTEGER,                 -- resolved via patient_identifiers / matching
  join_confidence REAL DEFAULT 0,

  patient_name_raw TEXT,
  phone_raw TEXT,

  appointment_date_raw TEXT,
  appointment_date_iso TEXT,          -- normalized later if needed

  payer_source_norm TEXT,             -- cash/insurance/mixed/unknown
  insurer_raw TEXT,
  insurer_name_norm TEXT,
  patient_share_pct INTEGER,
  pct_detected INTEGER,

  amount_patient REAL,
  amount_insurer REAL,
  net_received REAL,

  -- quality & traceability
  parse_status TEXT DEFAULT 'pending',
  parse_error TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT,

  FOREIGN KEY(patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_payments_clean_patient_id ON payments_clean(patient_id);
CREATE INDEX IF NOT EXISTS idx_payments_clean_record_no ON payments_clean(record_no);
CREATE INDEX IF NOT EXISTS idx_payments_clean_loaded_at ON payments_clean(loaded_at);