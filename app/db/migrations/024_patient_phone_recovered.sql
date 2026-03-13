-- Migration 024: patient_phone_recovered
-- Links recovered phones to patients for coverage metric (goal >= 90%).

CREATE TABLE IF NOT EXISTS patient_phone_recovered (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL,
    mobile      TEXT,
    landline    TEXT,
    source      TEXT NOT NULL,   -- 'patients' | 'stg_payments' | 'appointment_recordno_bridge'
    confidence  REAL NOT NULL DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(patient_id)
);

CREATE INDEX IF NOT EXISTS idx_patient_phone_recovered ON patient_phone_recovered(patient_id);
