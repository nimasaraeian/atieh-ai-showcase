-- =============================================================================
-- Phase 4 — Multi-hop Identity Graph Propagation (graph model)
-- Does NOT update patients or payments.patient_id.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. phase4_patient_graph_nodes
-- Nodes: anchor patients, unrecovered patients, payment/appointment rows as entities
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_patient_graph_nodes (
    node_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    node_type        TEXT NOT NULL,   -- 'anchor_patient' | 'unrecovered_patient' | 'payment_row' | 'appointment_row'
    patient_id       INTEGER,         -- set for patient nodes
    source_type      TEXT,            -- 'payment' | 'appointment' | NULL for patient
    source_row_id    INTEGER,         -- payments_staging_id or appointment_staging_id
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- 2. phase4_patient_graph_edges
-- Edges: link between nodes (e.g. patient has phone X, row has phone X)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_patient_graph_edges (
    edge_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node_id     INTEGER NOT NULL,
    to_node_id       INTEGER NOT NULL,
    edge_type        TEXT NOT NULL,   -- 'phone_match' | 'name_match' | 'same_cluster'
    evidence_type    TEXT NOT NULL,   -- 'phone_primary' | 'phone_all' | 'name_key'
    evidence_value   TEXT NOT NULL,
    observation_count INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (from_node_id) REFERENCES phase4_patient_graph_nodes(node_id),
    FOREIGN KEY (to_node_id) REFERENCES phase4_patient_graph_nodes(node_id)
);

-- -----------------------------------------------------------------------------
-- 3. phase4_phone_patient_links
-- phone_norm -> patient_id (and cluster_id when from anchor side) with source and count
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_phone_patient_links (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_norm        TEXT NOT NULL,
    patient_id        INTEGER NOT NULL,
    cluster_id        INTEGER,         -- anchor patient_id when link is from anchor evidence
    source_type       TEXT NOT NULL,   -- 'patient' | 'payment' | 'appointment'
    source_row_id     INTEGER,         -- patient_id or staging id
    is_primary        INTEGER NOT NULL DEFAULT 0,  -- 1 if phone_primary_norm
    observation_count INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- 4. phase4_name_patient_links
-- patient_name_key -> patient_id / cluster_id with source and count
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_name_patient_links (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name_key  TEXT NOT NULL,
    patient_id       INTEGER NOT NULL,
    cluster_id        INTEGER,
    source_type       TEXT NOT NULL,
    source_row_id     INTEGER,
    observation_count INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- 5. phase4_cluster_candidates
-- Unrecovered patient -> cluster (anchor) with evidence flags and score
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_cluster_candidates (
    candidate_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    unrecovered_patient_id    INTEGER NOT NULL,
    cluster_id                INTEGER NOT NULL,
    phone_primary_match       INTEGER NOT NULL DEFAULT 0,
    phone_all_match           INTEGER NOT NULL DEFAULT 0,
    name_key_match            INTEGER NOT NULL DEFAULT 0,
    repeated_anchored_phone   INTEGER NOT NULL DEFAULT 0,
    name_support_same_phone_cluster INTEGER NOT NULL DEFAULT 0,
    cross_source_evidence     INTEGER NOT NULL DEFAULT 0,
    repeated_obs_count        INTEGER NOT NULL DEFAULT 0,
    score_raw                 REAL,
    propagation_rule          TEXT,
    confidence_level          TEXT,
    match_status              TEXT NOT NULL DEFAULT 'candidate',
    diagnostics_json          TEXT,
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (unrecovered_patient_id) REFERENCES patients(id),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- 6. phase4_cluster_promoted
-- Promoted links only
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_cluster_promoted (
    promoted_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    unrecovered_patient_id    INTEGER NOT NULL,
    cluster_id                INTEGER NOT NULL,
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
-- 7. phase4_patient_recovered
-- Distinct recovered patient_id with cluster_id and recovery source
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_patient_recovered (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id          INTEGER NOT NULL UNIQUE,
    cluster_id          INTEGER NOT NULL,
    recovery_source     TEXT NOT NULL,   -- 'anchor_phase2' | 'phase3b_promoted' | 'phase4_promoted'
    propagation_rule    TEXT,
    confidence_level    TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (cluster_id) REFERENCES patients(id)
);

-- -----------------------------------------------------------------------------
-- 8. phase4_ambiguity_review
-- Unrecovered patients with competing targets (not promoted)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phase4_ambiguity_review (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    unrecovered_patient_id  INTEGER NOT NULL,
    candidate_cluster_ids  TEXT NOT NULL,   -- JSON array of cluster_id
    scores_json             TEXT,           -- JSON array of scores
    best_score              REAL,
    second_best_score       REAL,
    margin                  REAL,
    reason                  TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (unrecovered_patient_id) REFERENCES patients(id)
);
