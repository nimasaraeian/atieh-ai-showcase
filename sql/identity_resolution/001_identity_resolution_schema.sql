-- =============================================================================
-- Identity Resolution Engine – Phase 1 Schema
-- Non-destructive: staging, normalized, candidate, and proposed cluster tables only.
-- Does NOT modify patients or payments.patient_id.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- D1) appointments_unified_staging
-- Raw imported rows from all yearly appointment Excel files
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments_unified_staging (
    staging_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file          TEXT    NOT NULL,
    shamsi_year          INTEGER NOT NULL,
    sheet_name           TEXT,
    source_row_number     INTEGER NOT NULL,
    appointment_date_raw TEXT,
    appointment_time_raw TEXT,
    patient_name_raw     TEXT,
    patient_last_name_raw TEXT,
    patient_name_combined_raw TEXT,
    phone_raw            TEXT,
    insurance_raw        TEXT,
    doctor_name_raw      TEXT,
    service_name_raw     TEXT,
    gender_raw           TEXT,
    notes_raw            TEXT,
    appointment_type_raw TEXT,
    record_no_raw        TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- -----------------------------------------------------------------------------
-- D2) identity_normalized_payments
-- Normalized identity fields from payments_unified_staging
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_normalized_payments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    payments_staging_id INTEGER NOT NULL,
    source_file         TEXT NOT NULL,
    shamsi_year         INTEGER NOT NULL,
    patient_name_raw    TEXT,
    patient_name_norm   TEXT,
    patient_name_key    TEXT,
    mobile_raw         TEXT,
    mobile_primary_norm TEXT,
    mobile_all_norm_json TEXT,
    national_id_raw    TEXT,
    national_id_norm   TEXT,
    record_no_raw      TEXT,
    record_no_norm     TEXT,
    admission_date_raw TEXT,
    admission_date_norm TEXT,
    net_received_raw   TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(payments_staging_id),
    FOREIGN KEY (payments_staging_id) REFERENCES payments_unified_staging(id)
);

-- -----------------------------------------------------------------------------
-- D3) identity_normalized_appointments
-- Normalized identity fields from appointments_unified_staging
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_normalized_appointments (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_staging_id INTEGER NOT NULL,
    source_file            TEXT NOT NULL,
    shamsi_year            INTEGER NOT NULL,
    patient_name_raw       TEXT,
    patient_name_norm      TEXT,
    patient_name_key       TEXT,
    phone_raw              TEXT,
    phone_primary_norm     TEXT,
    phone_all_norm_json    TEXT,
    national_id_raw        TEXT,
    national_id_norm       TEXT,
    record_no_raw          TEXT,
    record_no_norm         TEXT,
    appointment_date_raw   TEXT,
    appointment_date_norm TEXT,
    doctor_name_raw        TEXT,
    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(appointment_staging_id),
    FOREIGN KEY (appointment_staging_id) REFERENCES appointments_unified_staging(staging_id)
);

-- -----------------------------------------------------------------------------
-- D4) patients_identity_normalized
-- Normalized identity fields from patients table (read-only source)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients_identity_normalized (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id          INTEGER NOT NULL UNIQUE,
    patient_name_raw    TEXT,
    patient_name_norm   TEXT,
    patient_name_key    TEXT,
    phone_raw           TEXT,
    phone_primary_norm  TEXT,
    phone_all_norm_json TEXT,
    national_id_raw     TEXT,
    national_id_norm    TEXT,
    record_no_raw       TEXT,
    record_no_norm      TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- D5) identity_candidate_matches
-- Candidate pairings between sources before final assignment
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_candidate_matches (
    candidate_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    left_source_type      TEXT NOT NULL,   -- 'payment' | 'appointment' | 'patient'
    left_row_id           INTEGER NOT NULL,
    right_source_type     TEXT NOT NULL,
    right_row_id          INTEGER NOT NULL,
    candidate_rule        TEXT NOT NULL,
    name_exact_flag       INTEGER NOT NULL DEFAULT 0,
    name_similarity_score REAL,
    phone_exact_flag      INTEGER NOT NULL DEFAULT 0,
    national_id_exact_flag INTEGER NOT NULL DEFAULT 0,
    record_no_exact_flag  INTEGER NOT NULL DEFAULT 0,
    same_year_flag        INTEGER NOT NULL DEFAULT 0,
    date_proximity_flag   INTEGER NOT NULL DEFAULT 0,
    score_raw             REAL,
    confidence_tier       TEXT,            -- 'A' | 'B' | 'C' | 'D'
    match_status          TEXT NOT NULL DEFAULT 'proposed',  -- 'proposed' | 'ambiguous' | 'rejected'
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

-- -----------------------------------------------------------------------------
-- D6) identity_clusters_proposed
-- Optional phase-1 proposed identity grouping (no final production assignment)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_clusters_proposed (
    cluster_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type    TEXT NOT NULL,
    source_row_id  INTEGER NOT NULL,
    confidence_tier TEXT,
    anchor_reason  TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
