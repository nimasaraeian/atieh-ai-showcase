BEGIN;

DELETE FROM identity_promotion_final_candidates;

INSERT INTO identity_promotion_final_candidates (
    record_no,
    patient_id,
    source_type,
    source_rule,
    confidence_score,
    final_status,
    final_notes
)
SELECT
    s.record_no,
    s.patient_id,
    s.source_type,
    s.source_rule,
    s.confidence_score,
    'READY_FOR_PROMOTION' AS final_status,
    'new-only staging candidate; not present in old mapping'
FROM identity_promotion_staging s
LEFT JOIN record_no_patient_map m
    ON m.record_no = s.record_no
WHERE s.staging_status = 'READY'
  AND m.record_no IS NULL;

COMMIT;
