-- Migration 001: Import Pipeline Tables
-- Idempotent migration for historical data import

-- Import runs tracking table
CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,  -- 'history', 'reference', 'manual'
    status TEXT NOT NULL DEFAULT 'running',  -- 'running', 'success', 'failed'
    started_at TEXT NOT NULL,
    completed_at TEXT,
    stats_json TEXT,  -- JSON with counts
    error_message TEXT,
    created_by TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_import_runs_status ON import_runs(status);
CREATE INDEX IF NOT EXISTS idx_import_runs_started ON import_runs(started_at DESC);

-- Staging table for reference data rows
CREATE TABLE IF NOT EXISTS stg_reference_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    sheet_name TEXT,
    row_number INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    parse_status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'ok', 'error'
    parse_error TEXT,
    FOREIGN KEY (import_run_id) REFERENCES import_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_stg_ref_import_run ON stg_reference_rows(import_run_id);
CREATE INDEX IF NOT EXISTS idx_stg_ref_status ON stg_reference_rows(parse_status);

-- Staging table for appointment rows from history files
CREATE TABLE IF NOT EXISTS stg_appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    sheet_name TEXT,
    row_number INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    parse_status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'ok', 'error'
    parse_error TEXT,
    patient_id INTEGER,  -- Link to final patient after processing
    appointment_id INTEGER,  -- Link to final appointment after processing
    FOREIGN KEY (import_run_id) REFERENCES import_runs(id),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

CREATE INDEX IF NOT EXISTS idx_stg_appt_import_run ON stg_appointments(import_run_id);
CREATE INDEX IF NOT EXISTS idx_stg_appt_status ON stg_appointments(parse_status);
CREATE INDEX IF NOT EXISTS idx_stg_appt_patient ON stg_appointments(patient_id);

-- Extend patients table with additional fields if needed
-- Add columns only if they don't exist (SQLite doesn't support IF NOT EXISTS for columns)
-- Check if columns exist before adding them in application code

-- Extend appointments table with source tracking
-- These will be added programmatically if not exists:
-- source_row_hash TEXT UNIQUE
-- raw_text_doctor TEXT
-- raw_text_service TEXT  
-- raw_text_insurance TEXT
-- import_run_id INTEGER

-- Create unique constraint on patients for deduplication
-- Unique by national_id when not null
CREATE UNIQUE INDEX IF NOT EXISTS idx_patients_national_id 
    ON patients(national_id) 
    WHERE national_id IS NOT NULL AND national_id != '';

-- Unique by phone_norm + full_name when phone_norm not null
-- Note: SQLite doesn't support functional indexes in older versions
-- We'll handle this in application code with normalization before insert

-- Appointments unique by source_row_hash (will be added as column)
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_source_hash 
--     ON appointments(source_row_hash) 
--     WHERE source_row_hash IS NOT NULL;
