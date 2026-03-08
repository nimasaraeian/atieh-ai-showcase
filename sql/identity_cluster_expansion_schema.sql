BEGIN;

CREATE TABLE IF NOT EXISTS identity_cluster_expansion (
    expansion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no TEXT,
    patient_id INTEGER,
    source_record_no TEXT,
    expansion_rule TEXT,
    confidence_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
