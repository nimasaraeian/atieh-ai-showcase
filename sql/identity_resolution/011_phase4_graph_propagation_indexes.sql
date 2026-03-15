-- =============================================================================
-- Phase 4 Graph Propagation — Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_p4nodes_type ON phase4_patient_graph_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_p4nodes_patient ON phase4_patient_graph_nodes(patient_id) WHERE patient_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_p4nodes_source ON phase4_patient_graph_nodes(source_type, source_row_id) WHERE source_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_p4edges_from ON phase4_patient_graph_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_p4edges_to ON phase4_patient_graph_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_p4edges_evidence ON phase4_patient_graph_edges(evidence_type, evidence_value);

CREATE INDEX IF NOT EXISTS idx_p4phone_phone ON phase4_phone_patient_links(phone_norm);
CREATE INDEX IF NOT EXISTS idx_p4phone_patient ON phase4_phone_patient_links(patient_id);
CREATE INDEX IF NOT EXISTS idx_p4phone_cluster ON phase4_phone_patient_links(cluster_id) WHERE cluster_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_p4name_key ON phase4_name_patient_links(patient_name_key);
CREATE INDEX IF NOT EXISTS idx_p4name_patient ON phase4_name_patient_links(patient_id);
CREATE INDEX IF NOT EXISTS idx_p4name_cluster ON phase4_name_patient_links(cluster_id) WHERE cluster_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_p4cand_unrecovered ON phase4_cluster_candidates(unrecovered_patient_id);
CREATE INDEX IF NOT EXISTS idx_p4cand_cluster ON phase4_cluster_candidates(cluster_id);
CREATE INDEX IF NOT EXISTS idx_p4cand_status ON phase4_cluster_candidates(match_status);
CREATE INDEX IF NOT EXISTS idx_p4cand_confidence ON phase4_cluster_candidates(confidence_level);

CREATE INDEX IF NOT EXISTS idx_p4prom_unrecovered ON phase4_cluster_promoted(unrecovered_patient_id);
CREATE INDEX IF NOT EXISTS idx_p4prom_cluster ON phase4_cluster_promoted(cluster_id);
CREATE INDEX IF NOT EXISTS idx_p4prom_rule ON phase4_cluster_promoted(propagation_rule);

CREATE INDEX IF NOT EXISTS idx_p4rec_patient ON phase4_patient_recovered(patient_id);
CREATE INDEX IF NOT EXISTS idx_p4rec_cluster ON phase4_patient_recovered(cluster_id);
CREATE INDEX IF NOT EXISTS idx_p4rec_source ON phase4_patient_recovered(recovery_source);

CREATE INDEX IF NOT EXISTS idx_p4amb_unrecovered ON phase4_ambiguity_review(unrecovered_patient_id);
