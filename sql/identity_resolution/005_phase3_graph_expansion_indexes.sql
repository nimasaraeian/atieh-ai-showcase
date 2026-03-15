-- =============================================================================
-- Identity Resolution Phase 3: Graph Expansion Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_anchor_phone_patient ON identity_anchor_phone_phase3(patient_id);
CREATE INDEX IF NOT EXISTS idx_anchor_phone_norm ON identity_anchor_phone_phase3(phone_norm);
CREATE UNIQUE INDEX IF NOT EXISTS idx_anchor_phone_patient_norm ON identity_anchor_phone_phase3(patient_id, phone_norm);

CREATE INDEX IF NOT EXISTS idx_anchor_recordno_patient ON identity_anchor_recordno_phase3(patient_id);
CREATE INDEX IF NOT EXISTS idx_anchor_recordno_norm ON identity_anchor_recordno_phase3(record_no_norm);
CREATE UNIQUE INDEX IF NOT EXISTS idx_anchor_recordno_patient_norm ON identity_anchor_recordno_phase3(patient_id, record_no_norm);

CREATE INDEX IF NOT EXISTS idx_anchor_name_patient ON identity_anchor_name_phase3(patient_id);
CREATE INDEX IF NOT EXISTS idx_anchor_name_key ON identity_anchor_name_phase3(patient_name_key);
CREATE UNIQUE INDEX IF NOT EXISTS idx_anchor_name_patient_key ON identity_anchor_name_phase3(patient_id, patient_name_key);

CREATE INDEX IF NOT EXISTS idx_exp_cand_source ON identity_expansion_candidates_phase3(source_type, source_row_id);
CREATE INDEX IF NOT EXISTS idx_exp_cand_target ON identity_expansion_candidates_phase3(target_patient_id);
CREATE INDEX IF NOT EXISTS idx_exp_cand_rule ON identity_expansion_candidates_phase3(expansion_rule);
CREATE INDEX IF NOT EXISTS idx_exp_cand_status ON identity_expansion_candidates_phase3(match_status);
CREATE INDEX IF NOT EXISTS idx_exp_cand_confidence ON identity_expansion_candidates_phase3(confidence_level);

CREATE INDEX IF NOT EXISTS idx_exp_prom_source ON identity_expansion_promoted_phase3(source_type, source_row_id);
CREATE INDEX IF NOT EXISTS idx_exp_prom_target ON identity_expansion_promoted_phase3(target_patient_id);
CREATE INDEX IF NOT EXISTS idx_exp_prom_rule ON identity_expansion_promoted_phase3(expansion_rule);

CREATE INDEX IF NOT EXISTS idx_cluster_members_cluster ON identity_cluster_members_phase3(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_members_patient ON identity_cluster_members_phase3(patient_id);
CREATE INDEX IF NOT EXISTS idx_cluster_members_source ON identity_cluster_members_phase3(source_type, source_row_id);
