INSERT INTO identity_cluster_expansion (
    record_no,
    patient_id,
    source_record_no,
    expansion_rule,
    confidence_score
)
SELECT
    irf.record_no,
    t.patient_id,
    t.record_no AS source_record_no,
    'PHONE_CLUSTER_EXPANSION_V1',
    0.85
FROM identity_record_features irf
JOIN tmp_safe_matches t
ON irf.matched_phone_norm = t.matched_phone_norm
WHERE irf.record_no <> t.record_no
AND irf.matched_phone_norm <> ''
AND LENGTH(irf.matched_phone_norm) = 11
AND NOT EXISTS (
    SELECT 1
    FROM record_no_patient_map m
    WHERE m.record_no = irf.record_no
)
AND NOT EXISTS (
    SELECT 1
    FROM identity_match_candidates c
    WHERE c.record_no = irf.record_no
);
