-- =============================================================================
-- Payment Identity Master V2 – Payments-first master identity architecture
-- Does NOT modify source tables. Built from payments_crm_code_all_years +
-- payments_unified_staging + (optional) payments_national_id_normalized.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. payment_identity_master
-- One row per financial identity entity (keyed by crm_patient_code).
-- Aggregated from all payment rows with that code.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payment_identity_master (
    identity_master_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    crm_patient_code          TEXT    NOT NULL UNIQUE,
    canonical_record_no       TEXT,
    canonical_patient_name    TEXT,
    patient_name_key          TEXT,
    canonical_national_id_norm TEXT,
    primary_phone_norm        TEXT,
    all_phones_json           TEXT,
    payment_rows_count        INTEGER NOT NULL DEFAULT 0,
    first_year                INTEGER,
    last_year                 INTEGER,
    total_net_received        REAL    NOT NULL DEFAULT 0,
    positive_net_received_sum  REAL    NOT NULL DEFAULT 0,
    negative_net_received_sum REAL    NOT NULL DEFAULT 0,
    source_rows_count         INTEGER NOT NULL DEFAULT 0,
    identity_strength_tier    TEXT    NOT NULL,
    identity_strength_rule    TEXT,
    created_at                TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pim_crm_code ON payment_identity_master(crm_patient_code);
CREATE INDEX IF NOT EXISTS idx_pim_name_key ON payment_identity_master(patient_name_key);
CREATE INDEX IF NOT EXISTS idx_pim_primary_phone ON payment_identity_master(primary_phone_norm);
CREATE INDEX IF NOT EXISTS idx_pim_national_id ON payment_identity_master(canonical_national_id_norm);
CREATE INDEX IF NOT EXISTS idx_pim_record_no ON payment_identity_master(canonical_record_no);


-- -----------------------------------------------------------------------------
-- 2. payment_identity_master_signals
-- Raw supporting signals per identity (observed values across payment rows).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payment_identity_master_signals (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    crm_patient_code          TEXT    NOT NULL,
    observed_record_no       TEXT,
    observed_name            TEXT,
    observed_name_key        TEXT,
    observed_phone           TEXT,
    observed_national_id     TEXT,
    observed_year            INTEGER,
    observation_count        INTEGER NOT NULL DEFAULT 0,
    created_at               TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pims_crm_code ON payment_identity_master_signals(crm_patient_code);
CREATE INDEX IF NOT EXISTS idx_pims_name_key ON payment_identity_master_signals(observed_name_key);
CREATE INDEX IF NOT EXISTS idx_pims_phone ON payment_identity_master_signals(observed_phone);
CREATE INDEX IF NOT EXISTS idx_pims_national_id ON payment_identity_master_signals(observed_national_id);


-- -----------------------------------------------------------------------------
-- 3. patient_master_link_v2
-- Link payment_identity_master (crm_patient_code) to patients_identity_normalized (patient_id).
-- link_tier: A | B | C | D. Tier D => review_flag=1.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_master_link_v2 (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    crm_patient_code          TEXT    NOT NULL,
    patient_id                INTEGER NOT NULL,
    link_tier                 TEXT    NOT NULL,
    link_rule                 TEXT    NOT NULL,
    confidence_score          REAL    NOT NULL DEFAULT 0,
    review_flag               INTEGER NOT NULL DEFAULT 0,
    review_reason             TEXT,
    created_at                TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    UNIQUE(crm_patient_code)
);

CREATE INDEX IF NOT EXISTS idx_pmlv2_patient_id ON patient_master_link_v2(patient_id);
CREATE INDEX IF NOT EXISTS idx_pmlv2_link_tier ON patient_master_link_v2(link_tier);
CREATE INDEX IF NOT EXISTS idx_pmlv2_review_flag ON patient_master_link_v2(review_flag);


-- -----------------------------------------------------------------------------
-- 4. master_patient_profile_v2
-- Final frontend/backend table: payment identity + patient link + display fields.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_patient_profile_v2 (
    master_profile_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                INTEGER NOT NULL,
    crm_patient_code          TEXT    NOT NULL,
    patient_name_canonical    TEXT,
    patient_name_key          TEXT,
    primary_phone             TEXT,
    all_phones_json           TEXT,
    national_id_norm          TEXT,
    payment_rows_count        INTEGER NOT NULL DEFAULT 0,
    total_net_received        REAL    NOT NULL DEFAULT 0,
    positive_net_received_sum REAL    NOT NULL DEFAULT 0,
    negative_net_received_sum REAL    NOT NULL DEFAULT 0,
    first_year                INTEGER,
    last_year                 INTEGER,
    identity_strength_tier    TEXT    NOT NULL,
    link_tier                 TEXT    NOT NULL,
    link_rule                 TEXT    NOT NULL,
    review_flag               INTEGER NOT NULL DEFAULT 0,
    review_reason             TEXT,
    created_at                TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    UNIQUE(crm_patient_code)
);

CREATE INDEX IF NOT EXISTS idx_mppv2_patient_id ON master_patient_profile_v2(patient_id);
CREATE INDEX IF NOT EXISTS idx_mppv2_crm_code ON master_patient_profile_v2(crm_patient_code);
CREATE INDEX IF NOT EXISTS idx_mppv2_name_key ON master_patient_profile_v2(patient_name_key);
CREATE INDEX IF NOT EXISTS idx_mppv2_primary_phone ON master_patient_profile_v2(primary_phone);
CREATE INDEX IF NOT EXISTS idx_mppv2_national_id ON master_patient_profile_v2(national_id_norm);
CREATE INDEX IF NOT EXISTS idx_mppv2_link_tier ON master_patient_profile_v2(link_tier);
