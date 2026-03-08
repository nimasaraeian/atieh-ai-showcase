BEGIN;

DELETE FROM identity_fuzzy_review_buckets;

INSERT INTO identity_fuzzy_review_buckets (
    review_id,
    record_no,
    patient_id,
    similarity_score,
    bucket_name,
    bucket_reason
)
SELECT
    f.review_id,
    f.record_no,
    f.patient_id,
    f.similarity_score,
    CASE
        WHEN f.similarity_score >= 0.96
             AND NOT EXISTS (
                 SELECT 1
                 FROM identity_name_risk_patterns r
                 WHERE
                    (f.record_name_norm LIKE '%' || r.pattern_a || '%' AND f.patient_name_norm LIKE '%' || r.pattern_b || '%')
                    OR
                    (f.record_name_norm LIKE '%' || r.pattern_b || '%' AND f.patient_name_norm LIKE '%' || r.pattern_a || '%')
             )
            THEN 'FAST_APPROVE'

        WHEN f.similarity_score >= 0.93
            THEN 'MANUAL_REVIEW'

        ELSE 'RISKY'
    END AS bucket_name,

    CASE
        WHEN f.similarity_score >= 0.96
             AND NOT EXISTS (
                 SELECT 1
                 FROM identity_name_risk_patterns r
                 WHERE
                    (f.record_name_norm LIKE '%' || r.pattern_a || '%' AND f.patient_name_norm LIKE '%' || r.pattern_b || '%')
                    OR
                    (f.record_name_norm LIKE '%' || r.pattern_b || '%' AND f.patient_name_norm LIKE '%' || r.pattern_a || '%')
             )
            THEN 'high similarity and no risky-name pattern'

        WHEN f.similarity_score >= 0.93
             AND EXISTS (
                 SELECT 1
                 FROM identity_name_risk_patterns r
                 WHERE
                    (f.record_name_norm LIKE '%' || r.pattern_a || '%' AND f.patient_name_norm LIKE '%' || r.pattern_b || '%')
                    OR
                    (f.record_name_norm LIKE '%' || r.pattern_b || '%' AND f.patient_name_norm LIKE '%' || r.pattern_a || '%')
             )
            THEN 'high similarity but risky-name pattern detected'

        WHEN f.similarity_score >= 0.93
            THEN 'medium-high similarity, manual verification recommended'

        ELSE 'lower similarity, risky for auto approval'
    END AS bucket_reason
FROM identity_fuzzy_review_candidates f;

COMMIT;
