BEGIN;

INSERT INTO record_no_patient_map (
    record_no,
    patient_id,
    phone_norm,
    match_method,
    confidence,
    evidence_count
)
SELECT
    f.record_no,
    f.patient_id,
    CASE
        WHEN f.source_type = 'SAFE_ENGINE' THEN ipf.primary_phone_norm
        WHEN f.source_type = 'FUZZY_FAST_APPROVE' THEN ipf.primary_phone_norm
        ELSE ipf.primary_phone_norm
    END AS phone_norm,
    CASE
        WHEN f.source_type = 'SAFE_ENGINE' THEN 'identity_safe_engine'
        WHEN f.source_type = 'FUZZY_FAST_APPROVE' THEN 'identity_fuzzy_fast_approve'
        ELSE 'identity_promotion'
    END AS match_method,
    CASE
        WHEN f.source_type = 'SAFE_ENGINE' THEN 0.95
        WHEN f.source_type = 'FUZZY_FAST_APPROVE' THEN f.confidence_score
        ELSE COALESCE(f.confidence_score, 0.90)
    END AS confidence,
    CASE
        WHEN f.source_type = 'SAFE_ENGINE' THEN 3
        WHEN f.source_type = 'FUZZY_FAST_APPROVE' THEN 4
        ELSE 2
    END AS evidence_count
FROM identity_promotion_final_candidates f
JOIN identity_patient_features ipf
    ON ipf.patient_id = f.patient_id
WHERE f.final_status = 'READY_FOR_PROMOTION'
  AND NOT EXISTS (
      SELECT 1
      FROM record_no_patient_map m
      WHERE m.record_no = f.record_no
  );

UPDATE identity_promotion_final_candidates
SET final_status = 'PROMOTED',
    final_notes = 'promoted to record_no_patient_map'
WHERE final_status = 'READY_FOR_PROMOTION';

COMMIT;
