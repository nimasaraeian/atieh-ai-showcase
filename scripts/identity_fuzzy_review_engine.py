import sqlite3
from difflib import SequenceMatcher

DB = r".\atieh_clinic.db"

SIM_THRESHOLD = 0.88
MAX_CANDIDATES_PER_RECORD = 3

def sim(a: str, b: str) -> float:
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

conn = sqlite3.connect(DB)
cur = conn.cursor()

# پاک کردن candidateهای review قبلی برای اجرای تمیز
cur.execute("DELETE FROM identity_fuzzy_review_candidates")

# فقط روی phone exact معتبر کار می‌کنیم
# فقط جاهایی که هنوز نه در mapping قدیمی match شده‌اند و نه در engine جدید
query = """
WITH candidate_base AS (
    SELECT
        irf.record_no,
        irf.matched_phone_norm,
        irf.payment_name_raw,
        irf.name_norm AS record_name_norm,
        irf.name_token_sorted AS record_name_token_sorted,
        ipf.patient_id,
        ipf.full_name AS patient_full_name,
        ipf.name_norm AS patient_name_norm,
        ipf.name_token_sorted AS patient_name_token_sorted
    FROM identity_record_features irf
    JOIN identity_patient_features ipf
      ON irf.matched_phone_norm = ipf.primary_phone_norm
    WHERE COALESCE(irf.matched_phone_norm, '') <> ''
      AND LENGTH(irf.matched_phone_norm) = 11
      AND SUBSTR(irf.matched_phone_norm, 1, 2) = '09'
      AND COALESCE(ipf.primary_phone_norm, '') <> ''
      AND LENGTH(ipf.primary_phone_norm) = 11
      AND SUBSTR(ipf.primary_phone_norm, 1, 2) = '09'
      AND COALESCE(irf.household_phone_flag, 0) = 0
      AND COALESCE(ipf.household_phone_flag, 0) = 0

      -- exclude already mapped old system
      AND NOT EXISTS (
          SELECT 1 FROM record_no_patient_map m
          WHERE m.record_no = irf.record_no
      )

      -- exclude already matched in safe engine
      AND NOT EXISTS (
          SELECT 1 FROM identity_match_candidates c
          WHERE c.record_no = irf.record_no
      )

      -- exclude stoplist names
      AND NOT EXISTS (
          SELECT 1
          FROM identity_name_stoplist s
          WHERE irf.name_norm LIKE '%' || s.stop_pattern || '%'
             OR ipf.name_norm LIKE '%' || s.stop_pattern || '%'
      )
)
SELECT
    record_no,
    matched_phone_norm,
    payment_name_raw,
    record_name_norm,
    record_name_token_sorted,
    patient_id,
    patient_full_name,
    patient_name_norm,
    patient_name_token_sorted
FROM candidate_base
"""

rows = cur.execute(query).fetchall()

# group by record_no
by_record = {}
for row in rows:
    rec = row[0]
    by_record.setdefault(rec, []).append(row)

insert_rows = []

for record_no, candidates in by_record.items():
    scored = []
    for row in candidates:
        (
            record_no,
            matched_phone_norm,
            payment_name_raw,
            record_name_norm,
            record_name_token_sorted,
            patient_id,
            patient_full_name,
            patient_name_norm,
            patient_name_token_sorted
        ) = row

        # fuzzy score روی هر دو فرم
        s1 = sim(record_name_norm, patient_name_norm)
        s2 = sim(record_name_token_sorted, patient_name_token_sorted)
        score = max(s1, s2)

        # exactها را کنار بگذار چون قبلاً گرفته شده‌اند
        if record_name_norm == patient_name_norm:
            continue
        if record_name_token_sorted == patient_name_token_sorted:
            continue

        if score >= SIM_THRESHOLD:
            scored.append((
                score,
                record_no,
                patient_id,
                matched_phone_norm,
                payment_name_raw,
                record_name_norm,
                record_name_token_sorted,
                patient_full_name,
                patient_name_norm,
                patient_name_token_sorted
            ))

    scored.sort(reverse=True, key=lambda x: x[0])

    # فقط چند candidate برتر برای هر record_no
    for item in scored[:MAX_CANDIDATES_PER_RECORD]:
        (
            score,
            record_no,
            patient_id,
            matched_phone_norm,
            payment_name_raw,
            record_name_norm,
            record_name_token_sorted,
            patient_full_name,
            patient_name_norm,
            patient_name_token_sorted
        ) = item

        insert_rows.append((
            record_no,
            patient_id,
            matched_phone_norm,
            payment_name_raw,
            record_name_norm,
            record_name_token_sorted,
            patient_full_name,
            patient_name_norm,
            patient_name_token_sorted,
            round(score, 4),
            "FUZZY_PHONE_EXACT_REVIEW_V1"
        ))

cur.executemany("""
INSERT INTO identity_fuzzy_review_candidates (
    record_no,
    patient_id,
    matched_phone_norm,
    payment_name_raw,
    record_name_norm,
    record_name_token_sorted,
    patient_full_name,
    patient_name_norm,
    patient_name_token_sorted,
    similarity_score,
    rule_name
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", insert_rows)

conn.commit()

count_all = cur.execute("SELECT COUNT(*) FROM identity_fuzzy_review_candidates").fetchone()[0]
count_records = cur.execute("SELECT COUNT(DISTINCT record_no) FROM identity_fuzzy_review_candidates").fetchone()[0]

print(f"Inserted fuzzy review candidates: {count_all}")
print(f"Distinct record_no in fuzzy review: {count_records}")

conn.close()
