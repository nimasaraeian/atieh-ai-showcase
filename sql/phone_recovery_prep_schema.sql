-- Phone Recovery Preparation
-- patients_phone_normalized, payments_phone_normalized, payments_phone_patient_match
-- Do NOT update final patient_id; intermediate tables only.

-- =============================================================================
-- 1. patients_phone_normalized (one row per patient with normalized 09xxxxxxxxx)
-- =============================================================================
CREATE TABLE IF NOT EXISTS patients_phone_normalized (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL UNIQUE,
    phone_raw       TEXT,
    phone_norm      TEXT,       -- 09xxxxxxxxx (11 digits) or NULL if invalid
    is_valid        INTEGER NOT NULL DEFAULT 0,  -- 1 if phone_norm is set
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_ppn_patient_id ON patients_phone_normalized(patient_id);
CREATE INDEX IF NOT EXISTS idx_ppn_phone_norm ON patients_phone_normalized(phone_norm);


-- =============================================================================
-- 2. payments_phone_normalized (from payments_unified_staging.phone_raw)
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments_phone_normalized (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    staging_id      INTEGER NOT NULL UNIQUE,
    phone_raw       TEXT,
    phone_norm      TEXT,       -- 09xxxxxxxxx (11 digits) or NULL if invalid
    is_valid        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (staging_id) REFERENCES payments_unified_staging(id)
);

CREATE INDEX IF NOT EXISTS idx_paypn_staging_id ON payments_phone_normalized(staging_id);
CREATE INDEX IF NOT EXISTS idx_paypn_phone_norm ON payments_phone_normalized(phone_norm);


-- =============================================================================
-- 3. payments_phone_patient_match (single | collision | no_match)
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments_phone_patient_match (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    staging_id      INTEGER NOT NULL,
    phone_norm      TEXT NOT NULL,
    patient_id      INTEGER,    -- NULL if no_match or collision
    match_status    TEXT NOT NULL,  -- 'single' | 'collision' | 'no_match'
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (staging_id) REFERENCES payments_unified_staging(id),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_pppm_staging_id ON payments_phone_patient_match(staging_id);
CREATE INDEX IF NOT EXISTS idx_pppm_phone_norm ON payments_phone_patient_match(phone_norm);
CREATE INDEX IF NOT EXISTS idx_pppm_patient_id ON payments_phone_patient_match(patient_id);
CREATE INDEX IF NOT EXISTS idx_pppm_match_status ON payments_phone_patient_match(match_status);
