import sqlite3

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"
TOTAL_PATIENTS = 140457

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA journal_mode=WAL;")
cur.execute("PRAGMA synchronous=NORMAL;")
cur.execute("PRAGMA temp_store=MEMORY;")
cur.execute("PRAGMA cache_size=-200000;")

for sql in [
    "DROP TABLE IF EXISTS patient_phone_lookup_unique",
    "DROP TABLE IF EXISTS payments_clean_phone_norm",
    "DROP TABLE IF EXISTS patient_phone_nid_evidence",
    "DROP TABLE IF EXISTS patient_phone_nid_summary",
    "DROP TABLE IF EXISTS patient_phone_nid_bridge_strict",
    "DROP TABLE IF EXISTS patient_phone_nid_bridge_tiered",
    "DROP TABLE IF EXISTS patient_phone_nid_increment_tierA",
    "DROP TABLE IF EXISTS patient_phone_nid_increment_tierAB",
    "DROP TABLE IF EXISTS patient_phone_nid_stats"
]:
    cur.execute(sql)
conn.commit()

# 1) فقط شماره‌های یکتای بیماران
cur.execute("""
CREATE TABLE patient_phone_lookup_unique AS
SELECT
    normalized_phone,
    MIN(patient_id) AS patient_id
FROM patient_phone_lookup
WHERE normalized_phone IS NOT NULL
  AND trim(normalized_phone) <> ''
GROUP BY normalized_phone
HAVING COUNT(DISTINCT patient_id) = 1
""")
cur.execute("CREATE INDEX idx_patient_phone_lookup_unique_phone ON patient_phone_lookup_unique(normalized_phone)")
cur.execute("CREATE INDEX idx_patient_phone_lookup_unique_pid ON patient_phone_lookup_unique(patient_id)")
conn.commit()

# 2) نرمال‌سازی phone_raw در payments_clean
cur.execute("""
CREATE TABLE payments_clean_phone_norm AS
SELECT
    payment_id,
    stg_payment_id,
    phone_raw,
    CASE
        WHEN phone_raw IS NULL OR trim(phone_raw) = '' THEN NULL
        ELSE
            CASE
                WHEN substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),1,4) = '0098'
                     AND length(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\','')) >= 14
                THEN substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),3)

                WHEN substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),1,2) = '98'
                     AND length(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\','')) = 12
                     AND substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),3,1) = '9'
                THEN replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\','')

                WHEN substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),1,1) = '0'
                     AND length(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\','')) = 11
                     AND substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),2,1) = '9'
                THEN '98' || substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),2)

                WHEN length(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\','')) = 10
                     AND substr(replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\',''),1,1) = '9'
                THEN '98' || replace(replace(replace(replace(replace(replace(replace(phone_raw,' ',''),'-',''),'(',''),')',''),'+',''),'/',''),'\','')

                ELSE NULL
            END
    END AS phone_norm
FROM payments_clean
WHERE phone_raw IS NOT NULL
  AND trim(phone_raw) <> ''
""")
cur.execute("CREATE INDEX idx_payments_clean_phone_norm_phone ON payments_clean_phone_norm(phone_norm)")
cur.execute("CREATE INDEX idx_payments_clean_phone_norm_stg ON payments_clean_phone_norm(stg_payment_id)")
conn.commit()

# 3) evidence
cur.execute("""
CREATE TABLE patient_phone_nid_evidence AS
SELECT DISTINCT
    u.patient_id,
    pnm.national_id,
    pcn.stg_payment_id AS payment_id,
    pcn.phone_norm AS normalized_phone,
    'exact_phone_lookup_to_payment_nid' AS match_method
FROM payments_clean_phone_norm pcn
JOIN patient_phone_lookup_unique u
  ON u.normalized_phone = pcn.phone_norm
JOIN payments_national_id_map pnm
  ON CAST(pnm.payment_id AS TEXT) = CAST(pcn.stg_payment_id AS TEXT)
WHERE pcn.phone_norm IS NOT NULL
  AND pnm.national_id IS NOT NULL
  AND trim(pnm.national_id) <> ''
""")
cur.execute("CREATE INDEX idx_patient_phone_nid_evidence_pid ON patient_phone_nid_evidence(patient_id)")
cur.execute("CREATE INDEX idx_patient_phone_nid_evidence_nid ON patient_phone_nid_evidence(national_id)")
conn.commit()

# 4) summary
cur.execute("""
CREATE TABLE patient_phone_nid_summary AS
SELECT
    patient_id,
    national_id,
    COUNT(*) AS supporting_payment_count,
    COUNT(DISTINCT payment_id) AS distinct_payment_count
FROM patient_phone_nid_evidence
GROUP BY patient_id, national_id
""")
cur.execute("CREATE INDEX idx_patient_phone_nid_summary_pid ON patient_phone_nid_summary(patient_id)")
cur.execute("CREATE INDEX idx_patient_phone_nid_summary_nid ON patient_phone_nid_summary(national_id)")
conn.commit()

# 5) strict bridge
cur.execute("""
CREATE TABLE patient_phone_nid_bridge_strict AS
WITH one_nid_patients AS (
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
JOIN one_nid_patients o
  ON o.patient_id = s.patient_id
WHERE s.distinct_payment_count >= 2
""")
cur.execute("CREATE INDEX idx_patient_phone_nid_bridge_strict_pid ON patient_phone_nid_bridge_strict(patient_id)")
cur.execute("CREATE INDEX idx_patient_phone_nid_bridge_strict_nid ON patient_phone_nid_bridge_strict(national_id)")
conn.commit()

# 6) tier
cur.execute("""
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
  ON t.national_id = b.national_id
""")
cur.execute("CREATE INDEX idx_patient_phone_nid_bridge_tiered_pid ON patient_phone_nid_bridge_tiered(patient_id)")
conn.commit()

# 7) increment
cur.execute("""
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
  AND b.identity_tier LIKE 'A%'
""")
cur.execute("CREATE INDEX idx_patient_phone_nid_increment_tierA_pid ON patient_phone_nid_increment_tierA(patient_id)")
conn.commit()

cur.execute("""
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
  AND (b.identity_tier LIKE 'A%' OR b.identity_tier LIKE 'B%')
""")
cur.execute("CREATE INDEX idx_patient_phone_nid_increment_tierAB_pid ON patient_phone_nid_increment_tierAB(patient_id)")
conn.commit()

# 8) stats
cur.execute("SELECT COUNT(*) FROM patient_phone_lookup")
patient_phone_lookup_rows = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_lookup_unique")
unique_phone_to_patient = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_nid_evidence")
evidence_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_nid_summary")
summary_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_nid_bridge_strict")
strict_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_nid_bridge_tiered WHERE identity_tier LIKE 'A%'")
tierA_bridge_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_nid_bridge_tiered WHERE identity_tier LIKE 'B%'")
tierB_bridge_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_nid_increment_tierA")
increment_A = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM patient_phone_nid_increment_tierAB")
increment_AB = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_phone_recovered_v2")
baseline = cur.fetchone()[0]

total_A = baseline + increment_A
coverage_A = round((total_A * 100.0) / TOTAL_PATIENTS, 2)

total_AB = baseline + increment_AB
coverage_AB = round((total_AB * 100.0) / TOTAL_PATIENTS, 2)

cur.execute("""
CREATE TABLE patient_phone_nid_stats AS
SELECT 'patient_phone_lookup_rows' AS metric, ?
UNION ALL SELECT 'unique_phone_to_patient', ?
UNION ALL SELECT 'evidence_rows', ?
UNION ALL SELECT 'summary_rows', ?
UNION ALL SELECT 'strict_bridge_rows', ?
UNION ALL SELECT 'tierA_bridge_rows', ?
UNION ALL SELECT 'tierB_bridge_rows', ?
UNION ALL SELECT 'increment_tierA', ?
UNION ALL SELECT 'increment_tierAB', ?
UNION ALL SELECT 'baseline_patients', ?
UNION ALL SELECT 'total_after_tierA', ?
UNION ALL SELECT 'coverage_after_tierA', ?
UNION ALL SELECT 'total_after_tierAB', ?
UNION ALL SELECT 'coverage_after_tierAB', ?
""", (
    str(patient_phone_lookup_rows),
    str(unique_phone_to_patient),
    str(evidence_count),
    str(summary_count),
    str(strict_count),
    str(tierA_bridge_count),
    str(tierB_bridge_count),
    str(increment_A),
    str(increment_AB),
    str(baseline),
    str(total_A),
    str(coverage_A),
    str(total_AB),
    str(coverage_AB),
))
conn.commit()

print("=== PATIENT PHONE -> NATIONAL ID BRIDGE (SQL FAST) ===")
print("patient_phone_lookup_rows :", patient_phone_lookup_rows)
print("unique_phone_to_patient   :", unique_phone_to_patient)
print("evidence_rows             :", evidence_count)
print("summary_rows              :", summary_count)
print("strict_bridge_rows        :", strict_count)
print("tierA_bridge_rows         :", tierA_bridge_count)
print("tierB_bridge_rows         :", tierB_bridge_count)
print("increment_tierA           :", increment_A)
print("increment_tierAB          :", increment_AB)
print("baseline_patients         :", baseline)
print("total_after_tierA         :", total_A)
print("coverage_after_tierA      :", coverage_A)
print("total_after_tierAB        :", total_AB)
print("coverage_after_tierAB     :", coverage_AB)

conn.close()
