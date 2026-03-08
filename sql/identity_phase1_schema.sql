PRAGMA foreign_keys = OFF;
BEGIN;

-- =========================================================
-- SAFE IDENTITY ENGINE - PHASE 1
-- Non-destructive schema only
-- =========================================================

CREATE TABLE IF NOT EXISTS identity_patient_features (
    patient_id INTEGER PRIMARY KEY,
    full_name TEXT,
    name_norm TEXT,
    name_token_sorted TEXT,
    primary_phone_norm TEXT,
    all_phones_norm TEXT,
    visit_count INTEGER,
    first_visit_date TEXT,
    last_visit_date TEXT,
    active_years TEXT,
    household_phone_flag INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identity_record_features (
    record_no TEXT PRIMARY KEY,
    payment_name_raw TEXT,
    name_norm TEXT,
    name_token_sorted TEXT,
    matched_phone_norm TEXT,
    payment_count INTEGER,
    first_payment_date TEXT,
    last_payment_date TEXT,
    active_years TEXT,
    household_phone_flag INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identity_match_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no TEXT NOT NULL,
    patient_id INTEGER NOT NULL,
    candidate_rule TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    conflict_count INTEGER DEFAULT 0,
    review_required INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identity_match_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    evidence_type TEXT NOT NULL,
    evidence_value TEXT,
    evidence_score REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identity_match_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    decision_status TEXT NOT NULL,
    decision_reason TEXT,
    approved_for_prod INTEGER DEFAULT 0,
    reviewed_by TEXT,
    reviewed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identity_match_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no TEXT NOT NULL,
    patient_id INTEGER,
    action_type TEXT NOT NULL,
    action_reason TEXT,
    action_meta TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identity_name_risk_patterns (
    risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_a TEXT,
    pattern_b TEXT,
    risk_level TEXT,
    notes TEXT
);

-- -------------------------
-- Helpful indexes
-- -------------------------

CREATE INDEX IF NOT EXISTS idx_ipf_name_norm
ON identity_patient_features(name_norm);

CREATE INDEX IF NOT EXISTS idx_ipf_name_token_sorted
ON identity_patient_features(name_token_sorted);

CREATE INDEX IF NOT EXISTS idx_ipf_primary_phone_norm
ON identity_patient_features(primary_phone_norm);

CREATE INDEX IF NOT EXISTS idx_irf_name_norm
ON identity_record_features(name_norm);

CREATE INDEX IF NOT EXISTS idx_irf_name_token_sorted
ON identity_record_features(name_token_sorted);

CREATE INDEX IF NOT EXISTS idx_irf_matched_phone_norm
ON identity_record_features(matched_phone_norm);

CREATE INDEX IF NOT EXISTS idx_imc_record_no
ON identity_match_candidates(record_no);

CREATE INDEX IF NOT EXISTS idx_imc_patient_id
ON identity_match_candidates(patient_id);

CREATE INDEX IF NOT EXISTS idx_imc_rule
ON identity_match_candidates(candidate_rule);

CREATE INDEX IF NOT EXISTS idx_imd_candidate_id
ON identity_match_decisions(candidate_id);

CREATE INDEX IF NOT EXISTS idx_ime_candidate_id
ON identity_match_evidence(candidate_id);

COMMIT;
