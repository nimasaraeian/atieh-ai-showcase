import sqlite3
import re
from collections import defaultdict

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"
TOTAL_PATIENTS = 140457

def norm_phone(x: str):
    if x is None:
        return None
    s = re.sub(r"\D+", "", str(x))
    if not s:
        return None

    if s.startswith("0098") and len(s) >= 14:
        s = s[2:]

    if s.startswith("98") and len(s) == 12 and s[2] == "9":
        return s

    if s.startswith("0") and len(s) == 11 and s[1] == "9":
        return "98" + s[1:]

    if len(s) == 10 and s[0] == "9":
        return "98" + s

    return None

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# -----------------------------
# cleanup
# -----------------------------
for sql in [
    "DROP TABLE IF EXISTS patient_phone_nid_evidence",
    "DROP TABLE IF EXISTS patient_phone_nid_summary",
    "DROP TABLE IF EXISTS patient_phone_nid_bridge_strict",
    "DROP TABLE IF EXISTS patient_phone_nid_bridge_tiered",
    "DROP TABLE IF EXISTS patient_phone_nid_increment_tierA",
    "DROP TABLE IF EXISTS patient_phone_nid_increment_tierAB",
    "DROP TABLE IF EXISTS patient_phone_nid_stats",
]:
    cur.execute(sql)
conn.commit()

# -----------------------------
# load patient phone lookup
# -----------------------------
cur.execute("""
    SELECT patient_id, normalized_phone
    FROM patient_phone_lookup
    WHERE patient_id IS NOT NULL
      AND normalized_phone IS NOT NULL
      AND trim(normalized_phone) <> ''
""")

phone_to_patients = defaultdict(set)
patient_phone_rows = 0

for patient_id, normalized_phone in cur.fetchall():
    p = norm_phone(normalized_phone)
    if p:
        phone_to_patients[p].add(int(patient_id))
        patient_phone_rows += 1

# فقط phone هایی که دقیقاً به یک patient تعلق دارند
unique_phone_to_patient = {}
for phone, pset in phone_to_patients.items():
    if len(pset) == 1:
        unique_phone_to_patient[phone] = next(iter(pset))

# -----------------------------
# build evidence from payments_clean + national_id_map
# -----------------------------
cur.execute("""
    SELECT
        pc.payment_id,
        pc.phone_raw,
        pnm.national_id
    FROM payments_clean pc
    JOIN payments_national_id_map pnm
      ON CAST(pnm.payment_id AS TEXT) = CAST(pc.stg_payment_id AS TEXT)
    WHERE pc.phone_raw IS NOT NULL
      AND trim(pc.phone_raw) <> ''
      AND pnm.national_id IS NOT NULL
      AND trim(pnm.national_id) <> ''
""")

evidence_rows = []
seen = set()

for payment_id, phone_raw, national_id in cur.fetchall():
    p = norm_phone(phone_raw)
    if not p:
        continue
    patient_id = unique_phone_to_patient.get(p)
    if patient_id is None:
        continue
    key = (patient_id, str(national_id), str(payment_id))
    if key in seen:
        continue
    seen.add(key)
    evidence_rows.append((patient_id, str(national_id), str(payment_id), p, "exact_phone_lookup_to_payment_nid"))

cur.execute("""
CREATE TABLE patient_phone_nid_evidence (
    patient_id INTEGER,
    national_id TEXT,
    payment_id TEXT,
    normalized_phone TEXT,
    match_method TEXT
)
""")
cur.executemany("""
INSERT INTO patient_phone_nid_evidence (
    patient_id, national_id, payment_id, normalized_phone, match_method
) VALUES (?, ?, ?, ?, ?)
""", evidence_rows)
cur.execute("CREATE INDEX idx_patient_phone_nid_evidence_pid ON patient_phone_nid_evidence(patient_id)")
cur.execute("CREATE INDEX idx_patient_phone_nid_evidence_nid ON patient_phone_nid_evidence(national_id)")
conn.commit()

# -----------------------------
# summary
# -----------------------------
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

# -----------------------------
# strict bridge:
# patient باید فقط یک national_id داشته باشد
# و حداقل 2 payment پشتوانه داشته باشد
# -----------------------------
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

# -----------------------------
# tier attach
# -----------------------------
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
cur.execute("CREATE INDEX idx_patient_phone_nid_bridge_tiered_tier ON patient_phone_nid_bridge_tiered(identity_tier)")
conn.commit()

# -----------------------------
# increment vs baseline
# -----------------------------
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

# -----------------------------
# stats
# -----------------------------
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
    str(patient_phone_rows),
    str(len(unique_phone_to_patient)),
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

print("=== PATIENT PHONE -> NATIONAL ID BRIDGE ===")
print("patient_phone_lookup_rows :", patient_phone_rows)
print("unique_phone_to_patient   :", len(unique_phone_to_patient))
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
