-- =============================================================================
-- Identity Resolution Phase 3B: Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_unrec_phase3b_phone ON unrecovered_patients_phase3b(phone_primary_norm) WHERE phone_primary_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unrec_phase3b_recordno ON unrecovered_patients_phase3b(record_no_norm) WHERE record_no_norm IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unrec_phase3b_name_key ON unrecovered_patients_phase3b(patient_name_key) WHERE patient_name_key IS NOT NULL AND TRIM(patient_name_key) <> '';

CREATE INDEX IF NOT EXISTS idx_pac_phase3b_unrecovered ON patient_anchor_candidates_phase3b(unrecovered_patient_id);
CREATE INDEX IF NOT EXISTS idx_pac_phase3b_anchor ON patient_anchor_candidates_phase3b(anchor_patient_id);
CREATE INDEX IF NOT EXISTS idx_pac_phase3b_rule ON patient_anchor_candidates_phase3b(candidate_rule);
CREATE INDEX IF NOT EXISTS idx_pac_phase3b_status ON patient_anchor_candidates_phase3b(match_status);
CREATE INDEX IF NOT EXISTS idx_pac_phase3b_confidence ON patient_anchor_candidates_phase3b(confidence_level);

CREATE INDEX IF NOT EXISTS idx_pap_phase3b_unrecovered ON patient_anchor_promoted_phase3b(unrecovered_patient_id);
CREATE INDEX IF NOT EXISTS idx_pap_phase3b_anchor ON patient_anchor_promoted_phase3b(anchor_patient_id);
CREATE INDEX IF NOT EXISTS idx_pap_phase3b_rule ON patient_anchor_promoted_phase3b(candidate_rule);

CREATE INDEX IF NOT EXISTS idx_pcm_phase3b_cluster ON patient_cluster_members_phase3b(cluster_id);
CREATE INDEX IF NOT EXISTS idx_pcm_phase3b_patient ON patient_cluster_members_phase3b(patient_id);
