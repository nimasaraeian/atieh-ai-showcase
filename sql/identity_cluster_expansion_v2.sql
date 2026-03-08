BEGIN;

DELETE FROM identity_cluster_expansion;

WITH safe_seed AS (
    SELECT
        c.record_no AS source_record_no,
        c.patient_id,
        irf.matched_phone_norm
    FROM identity_match_candidates c
    JOIN identity_record_features irf
        ON irf.record_no = c.record_no
    WHERE c.review_required = 0
      AND COALESCE(irf.matched_phone_norm, '') <> ''
      AND LENGTH(irf.matched_phone_norm) = 11
      AND SUBSTR(irf.matched_phone_norm, 1, 2) = '09'
      AND COALESCE(irf.household_phone_flag, 0) = 0
),
expansion_candidates AS (
    SELECT
        irf.record_no,
        ss.patient_id,
        ss.source_record_no,
        irf.matched_phone_norm,
        irf.name_norm AS record_name_norm,
        ipf.name_norm AS patient_name_norm,
        irf.household_phone_flag
    FROM identity_record_features irf
    JOIN safe_seed ss
        ON irf.matched_phone_norm = ss.matched_phone_norm
    JOIN identity_patient_features ipf
        ON ipf.patient_id = ss.patient_id
    WHERE irf.record_no <> ss.source_record_no
      AND COALESCE(irf.matched_phone_norm, '') <> ''
      AND LENGTH(irf.matched_phone_norm) = 11
      AND SUBSTR(irf.matched_phone_norm, 1, 2) = '09'
      AND COALESCE(irf.household_phone_flag, 0) = 0

      -- already mapped in old mapping
      AND NOT EXISTS (
          SELECT 1
          FROM record_no_patient_map m
          WHERE m.record_no = irf.record_no
      )

      -- already matched in new engine
      AND NOT EXISTS (
          SELECT 1
          FROM identity_match_candidates c
          WHERE c.record_no = irf.record_no
      )

      -- exclude generic names
      AND NOT EXISTS (
          SELECT 1
          FROM identity_name_stoplist s
          WHERE irf.name_norm LIKE '%' || s.stop_pattern || '%'
             OR ipf.name_norm LIKE '%' || s.stop_pattern || '%'
      )

      -- exclude risky name pairs
      AND NOT EXISTS (
          SELECT 1
          FROM identity_name_risk_patterns r
          WHERE
            (irf.name_norm LIKE '%' || r.pattern_a || '%' AND ipf.name_norm LIKE '%' || r.pattern_b || '%')
            OR
            (irf.name_norm LIKE '%' || r.pattern_b || '%' AND ipf.name_norm LIKE '%' || r.pattern_a || '%')
      )
)
INSERT INTO identity_cluster_expansion (
    record_no,
    patient_id,
    source_record_no,
    expansion_rule,
    confidence_score
)
SELECT
    ec.record_no,
    ec.patient_id,
    ec.source_record_no,
    'PHONE_CLUSTER_EXPANSION_V2' AS expansion_rule,
    0.85 AS confidence_score
FROM expansion_candidates ec
WHERE NOT EXISTS (
    SELECT 1
    FROM identity_cluster_expansion x
    WHERE x.record_no = ec.record_no
      AND x.patient_id = ec.patient_id
);

COMMIT;
