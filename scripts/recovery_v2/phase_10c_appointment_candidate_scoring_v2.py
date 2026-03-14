import sqlite3
import re

db = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"

conn = sqlite3.connect(db, timeout=60)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("START PHASE 10C V2", flush=True)

cur.executescript("""
DROP TABLE IF EXISTS unrecovered_appointment_candidates_scored_v2;

CREATE TABLE unrecovered_appointment_candidates_scored_v2 (
    patient_id INTEGER,
    patient_name TEXT,
    appointment_name TEXT,
    phone_candidate_raw TEXT,
    best_mobile TEXT,
    recordno_candidate TEXT,
    evidence_count INTEGER,
    duplicate_name_group INTEGER,
    confidence_score REAL,
    confidence_tier TEXT
);
""")

def normalize_digits(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    return s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

def normalize_mobile_token(n: str) -> str:
    if not n:
        return ""
    n = normalize_digits(n)
    n = re.sub(r"\D", "", n)

    if len(n) == 11 and n.startswith("09"):
        return n

    if len(n) == 10 and n.startswith("9"):
        return "0" + n

    if len(n) == 12 and n.startswith("98") and n[2] == "9":
        return "0" + n[2:]

    return ""

def extract_all_digit_runs(raw: str):
    if raw is None:
        return []
    s = normalize_digits(str(raw))
    return re.findall(r"\d+", s)

def extract_best_mobile(raw: str) -> str:
    nums = extract_all_digit_runs(raw)

    # اول موبایل‌های صریح را پیدا کن
    for n in nums:
        m = normalize_mobile_token(n)
        if m:
            return m

    return ""

dup_names = set()
for row in cur.execute("""
SELECT patient_name
FROM unrecovered_appointment_candidates
GROUP BY patient_name
HAVING COUNT(DISTINCT patient_id) > 1
""").fetchall():
    dup_names.add(row["patient_name"])

rows = cur.execute("""
SELECT
    patient_id,
    patient_name,
    appointment_name,
    phone_candidate,
    recordno_candidate,
    evidence_count
FROM unrecovered_appointment_candidates
""").fetchall()

print(f"rows loaded: {len(rows):,}", flush=True)
print(f"duplicate patient_name groups: {len(dup_names):,}", flush=True)

insert_sql = """
INSERT INTO unrecovered_appointment_candidates_scored_v2 (
    patient_id,
    patient_name,
    appointment_name,
    phone_candidate_raw,
    best_mobile,
    recordno_candidate,
    evidence_count,
    duplicate_name_group,
    confidence_score,
    confidence_tier
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

high = 0
medium = 0
low = 0

for i, row in enumerate(rows, start=1):
    patient_id = row["patient_id"]
    patient_name = row["patient_name"]
    appointment_name = row["appointment_name"]
    phone_candidate_raw = row["phone_candidate"]
    recordno_candidate = row["recordno_candidate"] or ""
    evidence_count = int(row["evidence_count"] or 0)

    best_mobile = extract_best_mobile(phone_candidate_raw)
    is_dup = 1 if patient_name in dup_names else 0

    score = 0.0

    if best_mobile:
        score += 5.0

    if evidence_count >= 10:
        score += 3.0
    elif evidence_count >= 5:
        score += 2.0
    elif evidence_count >= 3:
        score += 1.5
    elif evidence_count >= 2:
        score += 1.0

    if recordno_candidate:
        score += 2.0

    if is_dup:
        score -= 2.5
    else:
        score += 2.5

    # HIGH امن‌تر ولی واقعی‌تر
    if best_mobile and evidence_count >= 5 and is_dup == 0:
        tier = "HIGH"
        high += 1
    elif best_mobile and evidence_count >= 2:
        tier = "MEDIUM"
        medium += 1
    else:
        tier = "LOW"
        low += 1

    cur.execute(insert_sql, (
        patient_id,
        patient_name,
        appointment_name,
        phone_candidate_raw,
        best_mobile,
        recordno_candidate,
        evidence_count,
        is_dup,
        round(score, 2),
        tier
    ))

    if i % 10000 == 0:
        conn.commit()
        print(f"processed: {i:,}", flush=True)

conn.commit()

print("\n=== PHASE 10C V2 SUMMARY ===", flush=True)
print(f"total_rows              : {len(rows):,}", flush=True)
print(f"HIGH                    : {high:,}", flush=True)
print(f"MEDIUM                  : {medium:,}", flush=True)
print(f"LOW                     : {low:,}", flush=True)

sample = cur.execute("""
SELECT
    patient_id,
    patient_name,
    phone_candidate_raw,
    best_mobile,
    evidence_count,
    duplicate_name_group,
    confidence_score,
    confidence_tier
FROM unrecovered_appointment_candidates_scored_v2
ORDER BY confidence_score DESC
LIMIT 30
""").fetchall()

print("\nTOP SAMPLE", flush=True)
for r in sample:
    print(tuple(r), flush=True)

conn.close()
