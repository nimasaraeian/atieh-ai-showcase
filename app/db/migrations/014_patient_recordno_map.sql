-- Mapping: patient_id <-> record_no with method and confidence
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS patient_recordno_map (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  record_no TEXT NOT NULL,
  patient_name_norm TEXT,
  phone_norm TEXT,
  match_method TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0,
  evidence_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(record_no),
  FOREIGN KEY(patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_patient_recordno_map_patient_id ON patient_recordno_map(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_recordno_map_record_no ON patient_recordno_map(record_no);

-- Unresolved / ambiguous candidates for review
CREATE TABLE IF NOT EXISTS patient_recordno_map_review (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  record_no TEXT NOT NULL,
  patient_name_norm TEXT,
  phone_norm TEXT,
  candidate_patient_ids TEXT,
  reason TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_recordno_review_record_no ON patient_recordno_map_review(record_no);
