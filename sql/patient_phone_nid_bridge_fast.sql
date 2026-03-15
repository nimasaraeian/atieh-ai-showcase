DROP TABLE IF EXISTS patient_phone_nid_evidence;
DROP TABLE IF EXISTS patient_phone_nid_summary;
DROP TABLE IF EXISTS patient_phone_nid_bridge_strict;
DROP TABLE IF EXISTS patient_phone_nid_bridge_tiered;
DROP TABLE IF EXISTS patient_phone_nid_increment_tierA;
DROP TABLE IF EXISTS patient_phone_nid_increment_tierAB;
DROP TABLE IF EXISTS patient_phone_nid_stats;

DROP INDEX IF EXISTS idx_ppu_phone;
DROP INDEX IF EXISTS idx_pcpn_phone;
DROP INDEX IF EXISTS idx_pcpn_stg;
DROP INDEX IF EXISTS idx_pnm_payment_id;

CREATE INDEX IF NOT EXISTS idx_ppu_phone ON patient_phone_lookup_unique(normalized_phone);
CREATE INDEX IF NOT EXISTS idx_pcpn_phone ON payments_clean_phone_norm(phone_norm);
CREATE INDEX IF NOT EXISTS idx_pcpn_stg ON payments_clean_phone_norm(stg_payment_id);
CREATE INDEX IF NOT EXISTS idx_pnm_payment_id ON payments_national_id_map(payment_id);

CREATE TABLE patient_phone_nid_evidence AS
SELECT DISTINCT
    u.patient_id,
    pnm.national_id,
    pcn.stg_payment_id AS payment_id,
    pcn.phone_norm AS normalized_phone
FROM patient_phone_lookup_unique u
JOIN payments_clean_phone_norm pcn
    ON pcn.phone_norm = u.normalized_phone
JOIN payments_national_id_map pnm
    ON pnm.payment_id = pcn.stg_payment_id
WHERE pcn.phone_norm IS NOT NULL
  AND pnm.national_id IS NOT NULL
  AND trim(pnm.national_id) <> '';

CREATE INDEX IF NOT EXISTS idx_ppne_pid ON patient_phone_nid_evidence(patient_id);
CREATE INDEX IF NOT EXISTS idx_ppne_nid ON patient_phone_nid_evidence(national_id);

CREATE TABLE patient_phone_nid_summary AS
SELECT
    patient_id,
    national_id,
    COUNT(*) AS supporting_payment_count,
    COUNT(DISTINCT payment_id) AS distinct_payment_count
FROM patient_phone_nid_evidence
GROUP BY patient_id, national_id;

CREATE INDEX IF NOT EXISTS idx_ppns_pid ON patient_phone_nid_summary(patient_id);
CREATE INDEX IF NOT EXISTS idx_ppns_nid ON patient_phone_nid_summary(national_id);

CREATE TABLE patient_phone_nid_bridge_strict AS
WITH one_nid AS (
    SELECT patient_id
    FROM patient_phone_nid_summary
    GROUP BY patient_id
    HAVING COUNT(DISTINCT national_id) = 1
)
SELECT
    s.patient_id,
    s.national_id,
    s.supporting_payment_count,
    s.distinct_payment_count,
    0.95 AS confidence,
    'exact_phone_lookup_strict_unique_nid' AS match_method
FROM patient_phone_nid_summary s
JOIN one_nid o
    ON o.patient_id = s.patient_id
WHERE s.distinct_payment_count >= 2;

CREATE INDEX IF NOT EXISTS idx_ppnbs_pid ON patient_phone_nid_bridge_strict(patient_id);
CREATE INDEX IF NOT EXISTS idx_ppnbs_nid ON patient_phone_nid_bridge_strict(national_id);

CREATE TABLE patient_phone_nid_bridge_tiered AS
SELECT
    b.patient_id,
    b.national_id,
    b.supporting_payment_count,
    b.distinct_payment_count,
    b.confidence,
    b.match_method,
    t.identity_tier
FROM patient_phone_nid_bridge_strict b
LEFT JOIN national_id_master_tiered t
    ON t.national_id = b.national_id;

CREATE INDEX IF NOT EXISTS idx_ppnbt_pid ON patient_phone_nid_bridge_tiered(patient_id);
CREATE INDEX IF NOT EXISTS idx_ppnbt_tier ON patient_phone_nid_bridge_tiered(identity_tier);

CREATE TABLE patient_phone_nid_increment_tierA AS
SELECT
    b.patient_id,
    b.national_id,
    b.supporting_payment_count,
    b.distinct_payment_count,
    b.confidence,
    b.match_method,
    b.identity_tier
FROM patient_phone_nid_bridge_tiered b
LEFT JOIN patient_phone_recovered_v2 r
    ON r.patient_id = b.patient_id
WHERE r.patient_id IS NULL
  AND b.identity_tier LIKE 'A%';

CREATE TABLE patient_phone_nid_increment_tierAB AS
SELECT
    b.patient_id,
    b.national_id,
    b.supporting_payment_count,
    b.distinct_payment_count,
    b.confidence,
    b.match_method,
    b.identity_tier
FROM patient_phone_nid_bridge_tiered b
LEFT JOIN patient_phone_recovered_v2 r
    ON r.patient_id = b.patient_id
WHERE r.patient_id IS NULL
  AND (b.identity_tier LIKE 'A%' OR b.identity_tier LIKE 'B%');

CREATE TABLE patient_phone_nid_stats AS
SELECT 'evidence_rows' AS metric, CAST((SELECT COUNT(*) FROM patient_phone_nid_evidence) AS TEXT)
UNION ALL
SELECT 'summary_rows', CAST((SELECT COUNT(*) FROM patient_phone_nid_summary) AS TEXT)
UNION ALL
SELECT 'strict_bridge_rows', CAST((SELECT COUNT(*) FROM patient_phone_nid_bridge_strict) AS TEXT)
UNION ALL
SELECT 'tierA_increment', CAST((SELECT COUNT(*) FROM patient_phone_nid_increment_tierA) AS TEXT)
UNION ALL
SELECT 'tierAB_increment', CAST((SELECT COUNT(*) FROM patient_phone_nid_increment_tierAB) AS TEXT)
UNION ALL
SELECT 'baseline_patients', CAST((SELECT COUNT(DISTINCT patient_id) FROM patient_phone_recovered_v2) AS TEXT);
