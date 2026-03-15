DROP TABLE IF EXISTS patient_identity_evidence_v2;
DROP TABLE IF EXISTS patient_phone_resolved_v2;
DROP TABLE IF EXISTS patient_phone_recovered_v2;
DROP TABLE IF EXISTS recovery_run_metrics_v2;

CREATE TABLE patient_identity_evidence_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    candidate_mobile TEXT,
    candidate_landline TEXT,
    source TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    match_rank INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE patient_phone_resolved_v2 (
    patient_id INTEGER PRIMARY KEY,
    mobile TEXT,
    landline TEXT,
    best_source TEXT,
    best_evidence_type TEXT,
    confidence REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE patient_phone_recovered_v2 (
    patient_id INTEGER PRIMARY KEY,
    mobile TEXT,
    landline TEXT,
    best_source TEXT,
    confidence REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE recovery_run_metrics_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_name TEXT NOT NULL,
    total_patients INTEGER,
    recovered_count INTEGER,
    coverage_percent REAL,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);