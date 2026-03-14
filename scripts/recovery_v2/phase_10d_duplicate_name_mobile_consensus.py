import sqlite3

db = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"
conn = sqlite3.connect(db, timeout=60)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("START PHASE 10D", flush=True)

cur.executescript("""
DROP TABLE IF EXISTS appointment_name_mobile_consensus_v1;

CREATE TABLE appointment_name_mobile_consensus_v1 AS
SELECT
    patient_name,
    COUNT(*) AS row_count,
    COUNT(DISTINCT patient_id) AS patient_id_count,
    COUNT(DISTINCT best_mobile) AS distinct_mobile_count,
    MIN(best_mobile) AS chosen_mobile,
    MAX(evidence_count) AS max_evidence
FROM unrecovered_appointment_candidates_scored_v2
WHERE TRIM(COALESCE(best_mobile,'')) <> ''
GROUP BY patient_name;

CREATE INDEX IF NOT EXISTS idx_anmc_name
ON appointment_name_mobile_consensus_v1(patient_name);
""")

summary = cur.execute("""
SELECT
    COUNT(*) AS total_name_groups,
    SUM(CASE WHEN distinct_mobile_count = 1 THEN 1 ELSE 0 END) AS consensus_groups,
    SUM(CASE WHEN distinct_mobile_count > 1 THEN 1 ELSE 0 END) AS ambiguous_groups
FROM appointment_name_mobile_consensus_v1
""").fetchone()

print("\nSUMMARY", flush=True)
print(dict(summary), flush=True)

sample = cur.execute("""
SELECT
    patient_name,
    row_count,
    patient_id_count,
    distinct_mobile_count,
    chosen_mobile,
    max_evidence
FROM appointment_name_mobile_consensus_v1
ORDER BY max_evidence DESC, row_count DESC
LIMIT 30
""").fetchall()

print("\nTOP SAMPLE", flush=True)
for r in sample:
    print(tuple(r), flush=True)

conn.close()
