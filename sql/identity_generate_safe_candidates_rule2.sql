BEGIN;

INSERT INTO identity_match_candidates (
    record_no,
    patient_id,
    candidate_rule,
    confidence_score,
    conflict_count,
    review_required
)
SELECT
    irf.record_no,
    ipf.patient_id,
    'SAFE_PHONE_TOKEN_SORT_EXACT_V1' AS candidate_rule,
    0.90 AS confidence_score,
    0 AS conflict_count,
    0 AS review_required
FROM identity_record_features irf
JOIN identity_patient_features ipf
    ON irf.matched_phone_norm = ipf.primary_phone_norm
   AND irf.name_token_sorted = ipf.name_token_sorted
WHERE COALESCE(irf.matched_phone_norm, '') <> ''
  AND COALESCE(ipf.primary_phone_norm, '') <> ''
  AND LENGTH(irf.matched_phone_norm) = 11
  AND LENGTH(ipf.primary_phone_norm) = 11
  AND SUBSTR(irf.matched_phone_norm, 1, 2) = '09'
  AND SUBSTR(ipf.primary_phone_norm, 1, 2) = '09'
  AND COALESCE(irf.name_token_sorted, '') <> ''
  AND COALESCE(ipf.name_token_sorted, '') <> ''
  AND COALESCE(irf.household_phone_flag, 0) = 0
  AND COALESCE(ipf.household_phone_flag, 0) = 0
  AND NOT EXISTS (
      SELECT 1
      FROM identity_match_candidates c
      WHERE c.record_no = irf.record_no
        AND c.patient_id = ipf.patient_id
  )
  AND NOT EXISTS (
      SELECT 1
      FROM identity_name_stoplist s
      WHERE irf.name_norm LIKE '%' || s.stop_pattern || '%'
         OR ipf.name_norm LIKE '%' || s.stop_pattern || '%'
  )
  AND NOT EXISTS (
      SELECT 1
      FROM identity_name_risk_patterns r
      WHERE
        (irf.name_norm LIKE '%' || r.pattern_a || '%' AND ipf.name_norm LIKE '%' || r.pattern_b || '%')
        OR
        (irf.name_norm LIKE '%' || r.pattern_b || '%' AND ipf.name_norm LIKE '%' || r.pattern_a || '%')
  );

UPDATE identity_match_candidates
SET conflict_count = (
    SELECT COUNT(*)
    FROM identity_match_candidates c2
    WHERE c2.record_no = identity_match_candidates.record_no
) - 1;

UPDATE identity_match_candidates
SET review_required = 1
WHERE conflict_count > 0;

INSERT INTO identity_match_evidence (candidate_id, evidence_type, evidence_value, evidence_score)
SELECT c.candidate_id, 'phone_exact_valid_mobile', 'exact standardized mobile phone', 0.45
FROM identity_match_candidates c
WHERE NOT EXISTS (
    SELECT 1 FROM identity_match_evidence e
    WHERE e.candidate_id = c.candidate_id
);

INSERT INTO identity_match_evidence (candidate_id, evidence_type, evidence_value, evidence_score)
SELECT c.candidate_id, 'token_sort_exact', 'exact token-sorted name match', 0.25
FROM identity_match_candidates c
WHERE c.candidate_rule = 'SAFE_PHONE_TOKEN_SORT_EXACT_V1'
  AND NOT EXISTS (
      SELECT 1 FROM identity_match_evidence e
      WHERE e.candidate_id = c.candidate_id
        AND e.evidence_type = 'token_sort_exact'
  );

INSERT INTO identity_match_evidence (candidate_id, evidence_type, evidence_value, evidence_score)
SELECT c.candidate_id, 'household_risk_check', 'household_phone_flag = 0 on both sides', 0.10
FROM identity_match_candidates c
WHERE c.candidate_rule = 'SAFE_PHONE_TOKEN_SORT_EXACT_V1'
  AND c.review_required = 0
  AND NOT EXISTS (
      SELECT 1 FROM identity_match_evidence e
      WHERE e.candidate_id = c.candidate_id
        AND e.evidence_type = 'household_risk_check'
  );

INSERT INTO identity_match_decisions (
    candidate_id,
    decision_status,
    decision_reason,
    approved_for_prod
)
SELECT
    c.candidate_id,
    CASE
        WHEN c.review_required = 0 AND c.conflict_count = 0 THEN 'SAFE_AUTO'
        ELSE 'REVIEW_HIGH_PRIORITY'
    END,
    CASE
        WHEN c.review_required = 0 AND c.conflict_count = 0
            THEN 'valid exact mobile phone + token-sorted exact name + unique candidate'
        ELSE 'multiple candidates for same record_no'
    END,
    0
FROM identity_match_candidates c
WHERE NOT EXISTS (
    SELECT 1
    FROM identity_match_decisions d
    WHERE d.candidate_id = c.candidate_id
);

INSERT INTO identity_match_audit_log (
    record_no,
    patient_id,
    action_type,
    action_reason,
    action_meta
)
SELECT
    c.record_no,
    c.patient_id,
    'CANDIDATE_CREATED',
    c.candidate_rule,
    'confidence=' || c.confidence_score || '; conflict_count=' || c.conflict_count || '; review_required=' || c.review_required
FROM identity_match_candidates c
WHERE c.candidate_rule = 'SAFE_PHONE_TOKEN_SORT_EXACT_V1'
  AND NOT EXISTS (
      SELECT 1
      FROM identity_match_audit_log a
      WHERE a.record_no = c.record_no
        AND a.patient_id = c.patient_id
        AND a.action_reason = c.candidate_rule
  );

COMMIT;
