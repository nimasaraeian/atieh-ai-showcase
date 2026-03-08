BEGIN;

CREATE TABLE IF NOT EXISTS identity_fuzzy_review_buckets (
    bucket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL,
    record_no TEXT NOT NULL,
    patient_id INTEGER NOT NULL,
    similarity_score REAL,
    bucket_name TEXT NOT NULL, -- FAST_APPROVE / MANUAL_REVIEW / RISKY
    bucket_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ifrb_review_id
ON identity_fuzzy_review_buckets(review_id);

CREATE INDEX IF NOT EXISTS idx_ifrb_record_no
ON identity_fuzzy_review_buckets(record_no);

COMMIT;
