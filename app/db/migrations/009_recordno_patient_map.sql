DROP TABLE IF EXISTS record_no_patient_map;

CREATE TABLE record_no_patient_map (
  record_no TEXT PRIMARY KEY,
  patient_id INTEGER,
  phone_norm TEXT,
  match_method TEXT NOT NULL,         -- 'phone_mode', 'direct_row', ...
  confidence REAL NOT NULL DEFAULT 0, -- 0..1
  evidence_count INTEGER NOT NULL DEFAULT 0,
  mapped_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rnpm_patient_id
ON record_no_patient_map(patient_id);

CREATE INDEX IF NOT EXISTS idx_patients_phone
ON patients(phone);