-- Migration 025: Patient Identity Resolver tables

-- Evidence table: multiple rows per patient from various sources
CREATE TABLE IF NOT EXISTS patient_identity_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    candidate_mobile TEXT,
    candidate_landline TEXT,
    candidate_record_no TEXT,
    evidence_name TEXT,
    source TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_patient_identity_evidence_patient ON patient_identity_evidence(patient_id);

-- Normalized patient lookup (populated by script)
CREATE TABLE IF NOT EXISTS patient_lookup_norm (
    patient_id INTEGER PRIMARY KEY,
    patient_name_norm TEXT,
    patient_phone_norm TEXT
);

CREATE INDEX IF NOT EXISTS idx_patient_lookup_norm_name ON patient_lookup_norm(patient_name_norm);
CREATE INDEX IF NOT EXISTS idx_patient_lookup_norm_phone ON patient_lookup_norm(patient_phone_norm);

-- patient_phone_recovered: script recreates with new schema each run
