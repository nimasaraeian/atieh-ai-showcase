-- =============================================================================
-- Master Patient Profile V1 – Safe, product-ready layer for reception/backend
-- Does NOT modify source tables. Built from promoted links + safety screens.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. master_patient_profile_v1
-- One row per (crm_patient_code, patient_id) that passed safety rules.
-- Safe for UI/API consumption.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_patient_profile_v1 (
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
    negative_net_received_sum  REAL    NOT NULL DEFAULT 0,
    first_year                INTEGER,
    last_year                 INTEGER,
    link_confidence           TEXT    NOT NULL,
    link_rule                 TEXT    NOT NULL,
    ambiguity_flag            INTEGER NOT NULL DEFAULT 0,
    ambiguity_reason          TEXT,
    created_at                TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    UNIQUE(crm_patient_code)
);

CREATE INDEX IF NOT EXISTS idx_mppv1_patient_id ON master_patient_profile_v1(patient_id);
CREATE INDEX IF NOT EXISTS idx_mppv1_crm_code ON master_patient_profile_v1(crm_patient_code);
CREATE INDEX IF NOT EXISTS idx_mppv1_name_key ON master_patient_profile_v1(patient_name_key);
CREATE INDEX IF NOT EXISTS idx_mppv1_primary_phone ON master_patient_profile_v1(primary_phone);
CREATE INDEX IF NOT EXISTS idx_mppv1_national_id_norm ON master_patient_profile_v1(national_id_norm);


-- -----------------------------------------------------------------------------
-- 2. master_patient_profile_review_queue
-- Unresolved or unsafe rows for manual review / future refinement.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_patient_profile_review_queue (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    crm_patient_code          TEXT    NOT NULL,
    candidate_patient_id      INTEGER,
    candidate_name            TEXT,
    candidate_phone           TEXT,
    ambiguity_reason          TEXT    NOT NULL,
    candidate_count           INTEGER NOT NULL DEFAULT 0,
    payment_rows_count        INTEGER NOT NULL DEFAULT 0,
    candidate_match_rule      TEXT,
    candidate_confidence      TEXT,
    created_at                TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (candidate_patient_id) REFERENCES patients(id)
);

CREATE INDEX IF NOT EXISTS idx_mpprq_crm_code ON master_patient_profile_review_queue(crm_patient_code);
CREATE INDEX IF NOT EXISTS idx_mpprq_candidate_patient_id ON master_patient_profile_review_queue(candidate_patient_id);
CREATE INDEX IF NOT EXISTS idx_mpprq_ambiguity_reason ON master_patient_profile_review_queue(ambiguity_reason);
