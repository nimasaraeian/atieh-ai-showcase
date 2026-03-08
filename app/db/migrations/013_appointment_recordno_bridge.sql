-- Bridge table: record_no from appointment/scheduling files to patient identity
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS appointment_recordno_bridge (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT NOT NULL,
  source_sheet TEXT NOT NULL,
  source_row INTEGER NOT NULL,
  record_no TEXT NOT NULL,
  patient_name_raw TEXT,
  patient_name_norm TEXT,
  phone_raw TEXT,
  phone_norm TEXT,
  appointment_date_raw TEXT,
  appointment_year INTEGER,
  evidence_type TEXT NOT NULL DEFAULT 'appointment_file_record_no',
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(source_file, source_sheet, source_row)
);

CREATE INDEX IF NOT EXISTS idx_appt_bridge_record_no ON appointment_recordno_bridge(record_no);
CREATE INDEX IF NOT EXISTS idx_appt_bridge_name_norm ON appointment_recordno_bridge(patient_name_norm);
CREATE INDEX IF NOT EXISTS idx_appt_bridge_phone_norm ON appointment_recordno_bridge(phone_norm);
CREATE INDEX IF NOT EXISTS idx_appt_bridge_year ON appointment_recordno_bridge(appointment_year);
