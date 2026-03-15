-- =============================================================================
-- Reception patient search view – V2 identity layer (master_patient_profile_v2).
-- Read-only. Primary source for reception search; no dependency on record_no.
-- Columns match master_patient_profile_v2 for backend query compatibility.
-- =============================================================================

DROP VIEW IF EXISTS reception_patient_search_view;
CREATE VIEW reception_patient_search_view AS
SELECT
    patient_id,
    crm_patient_code,
    patient_name_canonical,
    patient_name_key,
    primary_phone,
    national_id_norm,
    payment_rows_count,
    total_net_received,
    positive_net_received_sum,
    negative_net_received_sum,
    first_year,
    last_year,
    identity_strength_tier,
    link_tier,
    link_rule,
    review_flag,
    review_reason,
    created_at
FROM master_patient_profile_v2;
