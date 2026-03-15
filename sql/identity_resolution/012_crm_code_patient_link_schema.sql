-- =============================================================================
-- Phase: CRM Code → Patient Linking
-- Bridges financial identity (crm_patient_code from payments) to patients table.
-- patients_identity_normalized.record_no_norm is empty; linking uses name_key + phone.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. crm_code_patient_link_candidates
-- Candidate (crm_patient_code, patient_id) with signals and tier
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_code_patient_link_candidates (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    crm_patient_code        TEXT    NOT NULL,
    patient_id               INTEGER NOT NULL,
    name_key_match          INTEGER NOT NULL DEFAULT 0,   -- 1 if patient_name_key exact match
    phone_primary_match      INTEGER NOT NULL DEFAULT 0,   -- 1 if payment phone set contains patient phone_primary_norm
    phone_any_match         INTEGER NOT NULL DEFAULT 0,   -- 1 if any payment phone in patient phone_all
    payment_rows_count      INTEGER NOT NULL DEFAULT 0,
    first_year              INTEGER,
    last_year               INTEGER,
    confidence_tier         TEXT    NOT NULL,            -- 'high' | 'medium' | 'low'
    match_rule               TEXT    NOT NULL,            -- e.g. 'name_exact+phone', 'name_exact', 'phone_only'
    cluster_support         INTEGER NOT NULL DEFAULT 0,    -- 1 if phase4 cluster evidence supports
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_ccplc_crm_code ON crm_code_patient_link_candidates(crm_patient_code);
CREATE INDEX IF NOT EXISTS idx_ccplc_patient_id ON crm_code_patient_link_candidates(patient_id);
CREATE INDEX IF NOT EXISTS idx_ccplc_tier ON crm_code_patient_link_candidates(confidence_tier);


-- -----------------------------------------------------------------------------
-- 2. crm_code_patient_link_promoted
-- One row per crm_code confidently linked to one patient_id
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_code_patient_link_promoted (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    crm_patient_code        TEXT    NOT NULL UNIQUE,
    patient_id               INTEGER NOT NULL,
    confidence_tier         TEXT    NOT NULL,
    match_rule               TEXT    NOT NULL,
    payment_rows_count      INTEGER NOT NULL DEFAULT 0,
    first_year              INTEGER,
    last_year               INTEGER,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_ccplp_patient_id ON crm_code_patient_link_promoted(patient_id);


-- -----------------------------------------------------------------------------
-- 3. crm_code_patient_link_ambiguous
-- Ambiguous cases: multiple patients per code or multiple codes per patient (when we flag)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_code_patient_link_ambiguous (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    crm_patient_code        TEXT    NOT NULL,
    patient_id               INTEGER NOT NULL,
    ambiguity_type          TEXT    NOT NULL,   -- 'multiple_patients_per_code' | 'multiple_codes_per_patient'
    candidate_count         INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_ccpla_crm_code ON crm_code_patient_link_ambiguous(crm_patient_code);
CREATE INDEX IF NOT EXISTS idx_ccpla_patient_id ON crm_code_patient_link_ambiguous(patient_id);
