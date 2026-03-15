-- =============================================================================
-- Identity Resolution Phase 3B: Anchored Patient Expansion
-- Links unrecovered patients (in patients table but not anchors) to anchor patients.
-- Does NOT update patients or payments.patient_id.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- unrecovered_patients_phase3b
-- All patients from patients_identity_normalized excluding anchor patients
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unrecovered_patients_phase3b (
    patient_id           INTEGER PRIMARY KEY,
    patient_name_key     TEXT,
    patient_name_norm    TEXT,
    phone_primary_norm   TEXT,
    record_no_norm       TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- patient_anchor_candidates_phase3b
-- Candidate links: unrecovered_patient_id -> anchor_patient_id with evidence
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_anchor_candidates_phase3b (
    candidate_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    unrecovered_patient_id       INTEGER NOT NULL,
    anchor_patient_id            INTEGER NOT NULL,
    phone_match_flag             INTEGER NOT NULL DEFAULT 0,
    record_no_match_flag         INTEGER NOT NULL DEFAULT 0,
    exact_name_match_flag        INTEGER NOT NULL DEFAULT 0,
    high_name_similarity_flag    INTEGER NOT NULL DEFAULT 0,
    repeated_cluster_phone_flag  INTEGER NOT NULL DEFAULT 0,
    repeated_cluster_recordno_flag INTEGER NOT NULL DEFAULT 0,
    support_signal_count         INTEGER NOT NULL DEFAULT 0,
    score_raw                    REAL,
    candidate_rule               TEXT,
    confidence_level             TEXT,
    match_status                 TEXT NOT NULL DEFAULT 'candidate',
    diagnostics_json             TEXT,
    created_at                   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (unrecovered_patient_id) REFERENCES patients(id),
    FOREIGN KEY (anchor_patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- patient_anchor_promoted_phase3b
-- Promoted links only (unrecovered patient = same identity as anchor)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_anchor_promoted_phase3b (
    promoted_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    unrecovered_patient_id   INTEGER NOT NULL,
    anchor_patient_id        INTEGER NOT NULL,
    candidate_rule           TEXT NOT NULL,
    support_signal_count     INTEGER NOT NULL DEFAULT 0,
    score_raw                REAL,
    confidence_level         TEXT NOT NULL,
    promotion_reason         TEXT,
    created_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (unrecovered_patient_id) REFERENCES patients(id),
    FOREIGN KEY (anchor_patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- patient_cluster_members_phase3b
-- Unified view: cluster_id = anchor_patient_id; members = anchor + promoted unrecovered
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_cluster_members_phase3b (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id          INTEGER NOT NULL,
    patient_id          INTEGER NOT NULL,
    source_origin       TEXT NOT NULL,
    rule_used           TEXT NOT NULL,
    confidence_level    TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);
