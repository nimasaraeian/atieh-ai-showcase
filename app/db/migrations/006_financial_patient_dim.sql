PRAGMA foreign_keys=ON;

-- 1) Financial patient dimension keyed by record_no
CREATE TABLE IF NOT EXISTS financial_patient_dim (
  record_no TEXT PRIMARY KEY,
  name_clean TEXT,
  phone_norm TEXT,
  first_seen_loaded_at TEXT,
  last_seen_loaded_at TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_fin_patient_phone_norm ON financial_patient_dim(phone_norm);

-- 2) Mapping from record_no -> patients.id when resolvable
CREATE TABLE IF NOT EXISTS patient_record_map (
  record_no TEXT PRIMARY KEY,
  patient_id INTEGER,
  match_method TEXT,          -- 'phone' | 'name' | 'manual'
  confidence REAL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT,
  FOREIGN KEY(patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_patient_record_map_patient_id ON patient_record_map(patient_id);