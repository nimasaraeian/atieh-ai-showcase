BEGIN;

DELETE FROM identity_match_evidence;
DELETE FROM identity_match_decisions;
DELETE FROM identity_match_candidates;
DELETE FROM identity_match_audit_log;

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
    'SAFE_PHONE_NAME_EXACT_V2' AS candidate_rule,
    0.95 AS confidence_score,
    0 AS conflict_count,
    0 AS review_required
FROM identity_record_features irf
JOIN identity_patient_features ipf
    ON irf.matched_phone_norm = ipf.primary_phone_norm
   AND irf.name_norm = ipf.name_norm
WHERE COALESCE(irf.matched_phone_norm, '') <> ''
  AND COALESCE(ipf.primary_phone_norm, '') <> ''
  AND LENGTH(irf.matched_phone_norm) = 11
  AND LENGTH(ipf.primary_phone_norm) = 11
  AND SUBSTR(irf.matched_phone_norm, 1, 2) = '09'
  AND SUBSTR(ipf.primary_phone_norm, 1, 2) = '09'
  AND COALESCE(irf.name_norm, '') <> ''
  AND COALESCE(ipf.name_norm, '') <> ''
  AND COALESCE(irf.household_phone_flag, 0) = 0
  AND COALESCE(ipf.household_phone_flag, 0) = 0;

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
SELECT candidate_id, 'phone_exact_valid_mobile', 'exact standardized mobile phone', 0.45
FROM identity_match_candidates;

INSERT INTO identity_match_evidence (candidate_id, evidence_type, evidence_value, evidence_score)
SELECT candidate_id, 'name_exact_norm', 'exact normalized name', 0.30
FROM identity_match_candidates;

INSERT INTO identity_match_evidence (candidate_id, evidence_type, evidence_value, evidence_score)
SELECT candidate_id, 'household_risk_check', 'household_phone_flag = 0 on both sides', 0.10
FROM identity_match_candidates
WHERE review_required = 0;

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
            THEN 'valid exact mobile phone + exact normalized name + unique candidate'
        ELSE 'multiple candidates for same record_no'
    END,
    0
FROM identity_match_candidates c;

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
FROM identity_match_candidates c;

COMMIT;
