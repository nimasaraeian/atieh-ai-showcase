BEGIN;

CREATE TABLE IF NOT EXISTS identity_promotion_staging (
    staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no TEXT NOT NULL,
    patient_id INTEGER NOT NULL,
    source_type TEXT NOT NULL, -- SAFE_ENGINE / FUZZY_FAST_APPROVE
    source_rule TEXT,
    confidence_score REAL,
    staging_status TEXT DEFAULT 'READY', -- READY / HOLD / REJECTED / PROMOTED
    staging_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ips_record_no
ON identity_promotion_staging(record_no);

CREATE INDEX IF NOT EXISTS idx_ips_patient_id
ON identity_promotion_staging(patient_id);

COMMIT;
