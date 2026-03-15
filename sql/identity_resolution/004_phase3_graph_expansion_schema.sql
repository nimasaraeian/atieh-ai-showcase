-- =============================================================================
-- Identity Resolution Phase 3: Graph Expansion Schema
-- Anchor-based expansion only. Does NOT update patients or payments.patient_id.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- C1) identity_anchor_patients_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_anchor_patients_phase3 (
    patient_id              INTEGER PRIMARY KEY,
    anchor_match_count      INTEGER NOT NULL DEFAULT 0,
    primary_anchor_count    INTEGER NOT NULL DEFAULT 0,
    high_sim_anchor_count   INTEGER NOT NULL DEFAULT 0,
    phone_only_anchor_count INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- C2) identity_anchor_profile_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_anchor_profile_phase3 (
    patient_id                 INTEGER PRIMARY KEY,
    phones_json                TEXT,
    phone_count                INTEGER NOT NULL DEFAULT 0,
    names_json                 TEXT,
    name_count                 INTEGER NOT NULL DEFAULT 0,
    record_nos_json            TEXT,
    record_no_count            INTEGER NOT NULL DEFAULT 0,
    years_json                 TEXT,
    year_count                 INTEGER NOT NULL DEFAULT 0,
    linked_payments_count       INTEGER NOT NULL DEFAULT 0,
    linked_appointments_count  INTEGER NOT NULL DEFAULT 0,
    linked_safe_matches_count  INTEGER NOT NULL DEFAULT 0,
    min_date_norm              TEXT,
    max_date_norm              TEXT,
    created_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- C3) identity_anchor_phone_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_anchor_phone_phase3 (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                   INTEGER NOT NULL,
    phone_norm                   TEXT NOT NULL,
    observation_count           INTEGER NOT NULL DEFAULT 0,
    appears_in_payments_count   INTEGER NOT NULL DEFAULT 0,
    appears_in_appointments_count INTEGER NOT NULL DEFAULT 0,
    appears_in_patients_count   INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- C4) identity_anchor_recordno_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_anchor_recordno_phase3 (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                  INTEGER NOT NULL,
    record_no_norm              TEXT NOT NULL,
    observation_count           INTEGER NOT NULL DEFAULT 0,
    appears_in_payments_count   INTEGER NOT NULL DEFAULT 0,
    appears_in_patients_count   INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- C5) identity_anchor_name_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_anchor_name_phase3 (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id                  INTEGER NOT NULL,
    patient_name_key            TEXT NOT NULL,
    patient_name_norm           TEXT,
    observation_count           INTEGER NOT NULL DEFAULT 0,
    appears_in_payments_count   INTEGER NOT NULL DEFAULT 0,
    appears_in_appointments_count INTEGER NOT NULL DEFAULT 0,
    appears_in_patients_count   INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- C6) identity_expansion_candidates_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_expansion_candidates_phase3 (
    expansion_candidate_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type                  TEXT NOT NULL,
    source_row_id                INTEGER NOT NULL,
    target_patient_id            INTEGER NOT NULL,
    phone_match_flag             INTEGER NOT NULL DEFAULT 0,
    record_no_match_flag         INTEGER NOT NULL DEFAULT 0,
    exact_name_match_flag        INTEGER NOT NULL DEFAULT 0,
    high_name_similarity_flag    INTEGER NOT NULL DEFAULT 0,
    same_year_flag               INTEGER NOT NULL DEFAULT 0,
    date_compatible_flag         INTEGER NOT NULL DEFAULT 0,
    repeated_cluster_phone_flag  INTEGER NOT NULL DEFAULT 0,
    repeated_cluster_recordno_flag INTEGER NOT NULL DEFAULT 0,
    support_signal_count         INTEGER NOT NULL DEFAULT 0,
    score_raw                    REAL,
    expansion_rule               TEXT,
    confidence_level             TEXT,
    match_status                 TEXT NOT NULL DEFAULT 'candidate',
    diagnostics_json             TEXT,
    created_at                   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (target_patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- C7) identity_expansion_promoted_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_expansion_promoted_phase3 (
    promoted_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type          TEXT NOT NULL,
    source_row_id        INTEGER NOT NULL,
    target_patient_id    INTEGER NOT NULL,
    expansion_rule       TEXT NOT NULL,
    support_signal_count INTEGER NOT NULL DEFAULT 0,
    score_raw            REAL,
    confidence_level     TEXT NOT NULL,
    promotion_reason     TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (target_patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- C8) identity_cluster_members_phase3
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_cluster_members_phase3 (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id           INTEGER NOT NULL,
    patient_id          INTEGER NOT NULL,
    source_type         TEXT NOT NULL,
    source_row_id       INTEGER NOT NULL,
    source_origin       TEXT NOT NULL,
    rule_used           TEXT NOT NULL,
    confidence_level    TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
