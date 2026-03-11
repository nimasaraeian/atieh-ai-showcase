-- Doctor dimension for clean analytics
CREATE TABLE IF NOT EXISTS doctor_dim (
  raw_doctor_text TEXT PRIMARY KEY,
  clean_doctor_name TEXT NOT NULL,
  doctor_specialty TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_doctor_dim_clean ON doctor_dim(clean_doctor_name);
