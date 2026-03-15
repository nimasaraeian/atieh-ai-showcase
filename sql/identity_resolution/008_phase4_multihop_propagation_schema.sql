-- =============================================================================
-- Identity Resolution Phase 4: Multi-hop Graph Propagation
-- Expanded cluster evidence from phase2 + phase3; safe graph-based propagation.
-- Does NOT update patients or payments.patient_id.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- identity_cluster_evidence_phase4
-- All phones, name_keys, record_nos per cluster from phase2 safe + phase3 promoted links
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_cluster_evidence_phase4 (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id          INTEGER NOT NULL,
    evidence_type       TEXT NOT NULL,   -- 'phone' | 'name_key' | 'record_no'
    evidence_value      TEXT NOT NULL,
    source_origin       TEXT NOT NULL,   -- 'phase2_safe' | 'phase3_promoted'
    source_type         TEXT NOT NULL,   -- 'payment' | 'appointment' | 'patient'
    source_row_id       INTEGER NOT NULL,
    observation_count   INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- identity_phase4_candidates
-- Unrecovered patient -> cluster (anchor) with match evidence
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_phase4_candidates (
    candidate_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    unrecovered_patient_id  INTEGER NOT NULL,
    cluster_id              INTEGER NOT NULL,
    phone_match_flag        INTEGER NOT NULL DEFAULT 0,
    name_key_match_flag     INTEGER NOT NULL DEFAULT 0,
    record_no_match_flag    INTEGER NOT NULL DEFAULT 0,
    high_name_sim_flag      INTEGER NOT NULL DEFAULT 0,
    repeated_in_cluster_phone  INTEGER NOT NULL DEFAULT 0,
    repeated_in_cluster_name   INTEGER NOT NULL DEFAULT 0,
    repeated_in_cluster_recordno INTEGER NOT NULL DEFAULT 0,
    shared_phone_across_clusters INTEGER NOT NULL DEFAULT 0,
    support_signal_count    INTEGER NOT NULL DEFAULT 0,
    score_raw               REAL,
    propagation_rule        TEXT,
    confidence_level        TEXT,
    match_status            TEXT NOT NULL DEFAULT 'candidate',
    diagnostics_json        TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (unrecovered_patient_id) REFERENCES patients(id),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- identity_phase4_promoted
-- Promoted multi-hop links only
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_phase4_promoted (
    promoted_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    unrecovered_patient_id   INTEGER NOT NULL,
    cluster_id               INTEGER NOT NULL,
    propagation_rule          TEXT NOT NULL,
    support_signal_count      INTEGER NOT NULL DEFAULT 0,
    score_raw                 REAL,
    confidence_level          TEXT NOT NULL,
    promotion_reason          TEXT,
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (unrecovered_patient_id) REFERENCES patients(id),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- identity_phase4_cluster_members
-- Unified cluster membership after phase4 propagation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_phase4_cluster_members (
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
