-- Unified Payments Staging + National ID Recovery Preparation
-- Phase: One staging table for all years; record_no optional; national_id match intermediate.

-- =============================================================================
-- 1. Unified staging table (all payment files, fixed column mapping)
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments_unified_staging (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file           TEXT    NOT NULL,   -- e.g. payments_1403_full.xlsx
    shamsi_year           INTEGER NOT NULL, -- e.g. 1403
    row_number            INTEGER NOT NULL,
    sheet_name            TEXT,
    loaded_at             TEXT    NOT NULL DEFAULT (datetime('now')),
    parse_status          TEXT    NOT NULL DEFAULT 'ok',
    parse_error           TEXT,

    -- Raw columns (fixed mapping: موبايل, كد ملي, خالص دريافتي, نام بيمار, تاريخ پذيرش, شماره پرونده optional)
    patient_name_raw      TEXT,
    phone_raw             TEXT,
    national_id_raw       TEXT,
    net_received_raw      TEXT,
    record_no             TEXT,             -- NULL if column missing (e.g. 1403)
    appointment_date_raw  TEXT,
    insurer_raw           TEXT,
    amount_patient_raw    TEXT,
    amount_insurer_raw    TEXT
);

CREATE INDEX IF NOT EXISTS idx_pus_source_file ON payments_unified_staging(source_file);
CREATE INDEX IF NOT EXISTS idx_pus_shamsi_year ON payments_unified_staging(shamsi_year);
CREATE INDEX IF NOT EXISTS idx_pus_national_id_raw ON payments_unified_staging(national_id_raw);
CREATE INDEX IF NOT EXISTS idx_pus_record_no ON payments_unified_staging(record_no);


-- =============================================================================
-- 2. National ID normalized (10 digits only) – for matching
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments_national_id_normalized (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    staging_id    INTEGER NOT NULL,
    national_id_raw  TEXT,
    national_id_norm TEXT,    -- digits only, length 10
    is_valid      INTEGER NOT NULL DEFAULT 0,  -- 1 if length = 10
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(staging_id),
    FOREIGN KEY (staging_id) REFERENCES payments_unified_staging(id)
);

CREATE INDEX IF NOT EXISTS idx_pnin_national_id_norm ON payments_national_id_normalized(national_id_norm);
CREATE INDEX IF NOT EXISTS idx_pnin_staging_id ON payments_national_id_normalized(staging_id);


-- =============================================================================
-- 3. Intermediate match table (do NOT update payments / patient_id here)
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments_national_id_patient_match (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    staging_id      INTEGER NOT NULL,
    national_id_norm TEXT NOT NULL,
    patient_id      INTEGER,             -- NULL if no_match or collision
    match_status    TEXT NOT NULL,       -- 'single' | 'collision' | 'no_match'
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (staging_id) REFERENCES payments_unified_staging(id),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_pnipm_staging_id ON payments_national_id_patient_match(staging_id);
CREATE INDEX IF NOT EXISTS idx_pnipm_patient_id ON payments_national_id_patient_match(patient_id);
CREATE INDEX IF NOT EXISTS idx_pnipm_national_id_norm ON payments_national_id_patient_match(national_id_norm);
CREATE INDEX IF NOT EXISTS idx_pnipm_match_status ON payments_national_id_patient_match(match_status);
