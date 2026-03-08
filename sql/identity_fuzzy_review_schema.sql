BEGIN;

CREATE TABLE IF NOT EXISTS identity_fuzzy_review_candidates (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no TEXT NOT NULL,
    patient_id INTEGER NOT NULL,
    matched_phone_norm TEXT,
    payment_name_raw TEXT,
    record_name_norm TEXT,
    record_name_token_sorted TEXT,
    patient_full_name TEXT,
    patient_name_norm TEXT,
    patient_name_token_sorted TEXT,
    similarity_score REAL,
    rule_name TEXT,
    review_status TEXT DEFAULT 'PENDING', -- PENDING / APPROVED / REJECTED
    review_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ifrc_record_no
ON identity_fuzzy_review_candidates(record_no);

CREATE INDEX IF NOT EXISTS idx_ifrc_patient_id
ON identity_fuzzy_review_candidates(patient_id);

CREATE INDEX IF NOT EXISTS idx_ifrc_phone
ON identity_fuzzy_review_candidates(matched_phone_norm);

COMMIT;
