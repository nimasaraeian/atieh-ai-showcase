BEGIN;

CREATE TABLE IF NOT EXISTS identity_promotion_final_candidates (
    final_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no TEXT NOT NULL,
    patient_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    source_rule TEXT,
    confidence_score REAL,
    final_status TEXT DEFAULT 'READY_FOR_PROMOTION', -- READY_FOR_PROMOTION / HELD / PROMOTED
    final_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ipfc_record_no
ON identity_promotion_final_candidates(record_no);

CREATE INDEX IF NOT EXISTS idx_ipfc_patient_id
ON identity_promotion_final_candidates(patient_id);

COMMIT;
