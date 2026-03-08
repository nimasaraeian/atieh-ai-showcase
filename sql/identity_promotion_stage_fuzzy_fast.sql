BEGIN;

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
    f.record_no,
    f.patient_id,
    'FUZZY_FAST_APPROVE' AS source_type,
    f.rule_name AS source_rule,
    f.similarity_score AS confidence_score,
    'READY' AS staging_status,
    'fuzzy review bucket fast_approve'
FROM identity_fuzzy_review_candidates f
JOIN identity_fuzzy_review_buckets b
    ON b.review_id = f.review_id
WHERE b.bucket_name = 'FAST_APPROVE'
  AND NOT EXISTS (
      SELECT 1
      FROM identity_promotion_staging s
      WHERE s.record_no = f.record_no
  );

COMMIT;
