-- =============================================================================
-- Identity Resolution Phase 4: Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_ice4_cluster ON identity_cluster_evidence_phase4(cluster_id);
CREATE INDEX IF NOT EXISTS idx_ice4_type_value ON identity_cluster_evidence_phase4(evidence_type, evidence_value);
CREATE INDEX IF NOT EXISTS idx_ice4_origin ON identity_cluster_evidence_phase4(source_origin);

CREATE INDEX IF NOT EXISTS idx_ip4c_unrecovered ON identity_phase4_candidates(unrecovered_patient_id);
CREATE INDEX IF NOT EXISTS idx_ip4c_cluster ON identity_phase4_candidates(cluster_id);
CREATE INDEX IF NOT EXISTS idx_ip4c_rule ON identity_phase4_candidates(propagation_rule);
CREATE INDEX IF NOT EXISTS idx_ip4c_status ON identity_phase4_candidates(match_status);
CREATE INDEX IF NOT EXISTS idx_ip4c_confidence ON identity_phase4_candidates(confidence_level);

CREATE INDEX IF NOT EXISTS idx_ip4p_unrecovered ON identity_phase4_promoted(unrecovered_patient_id);
CREATE INDEX IF NOT EXISTS idx_ip4p_cluster ON identity_phase4_promoted(cluster_id);
CREATE INDEX IF NOT EXISTS idx_ip4p_rule ON identity_phase4_promoted(propagation_rule);

CREATE INDEX IF NOT EXISTS idx_ip4m_cluster ON identity_phase4_cluster_members(cluster_id);
CREATE INDEX IF NOT EXISTS idx_ip4m_patient ON identity_phase4_cluster_members(patient_id);
