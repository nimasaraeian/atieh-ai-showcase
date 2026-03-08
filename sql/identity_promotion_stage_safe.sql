BEGIN;

DELETE FROM identity_promotion_staging;

INSERT INTO identity_promotion_staging (
    record_no,
    patient_id,
    source_type,
    source_rule,
    confidence_score,
    staging_status,
    staging_notes
)
SELECT
    c.record_no,
    c.patient_id,
    'SAFE_ENGINE' AS source_type,
    c.candidate_rule AS source_rule,
    c.confidence_score,
    'READY' AS staging_status,
    'safe engine auto-approved'
FROM identity_match_candidates c
JOIN identity_match_decisions d
    ON d.candidate_id = c.candidate_id
WHERE d.decision_status = 'SAFE_AUTO'
  AND c.review_required = 0;

COMMIT;
