import sqlite3
import re

db = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"

conn = sqlite3.connect(db, timeout=60)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("START PHASE 10B")

cur.executescript("""

DROP TABLE IF EXISTS unrecovered_appointment_candidates;

CREATE TABLE unrecovered_appointment_candidates (
    patient_id INTEGER,
    patient_name TEXT,
    appointment_name TEXT,
    phone_candidate TEXT,
    recordno_candidate TEXT,
    evidence_count INTEGER
);

""")

def normalize_name(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("ي","ی").replace("ك","ک")
    s = re.sub(r"[()0-9]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def extract_record_no(s):
    if not s:
        return ""
    m = re.search(r"\((\d+)\)", str(s))
    return m.group(1) if m else ""

unrecovered = cur.execute("""

SELECT
    p.id AS patient_id,
    p.name AS patient_name
FROM patients p
LEFT JOIN patient_phone_recovered_v2 r
ON r.patient_id = p.id
WHERE r.patient_id IS NULL

""").fetchall()

print("unrecovered patients:", len(unrecovered))

appointments = cur.execute("""

SELECT
    patient_name_raw,
    phone_raw
FROM appointment_recordno_bridge

""").fetchall()

print("appointments loaded:", len(appointments))

appointment_index = {}

for row in appointments:

    name = normalize_name(row["patient_name_raw"])
    phone = row["phone_raw"]
    rec = extract_record_no(row["patient_name_raw"])

    if not name:
        continue

    if name not in appointment_index:
        appointment_index[name] = []

    appointment_index[name].append((phone, rec, row["patient_name_raw"]))


insert_sql = """
INSERT INTO unrecovered_appointment_candidates
VALUES (?, ?, ?, ?, ?, ?)
"""

count = 0

for i, row in enumerate(unrecovered, start=1):

    pid = row["patient_id"]
    pname = row["patient_name"]
    norm = normalize_name(pname)

    if norm in appointment_index:

        entries = appointment_index[norm]

        evidence = len(entries)

        phone = entries[0][0]
        rec = entries[0][1]
        raw = entries[0][2]

        cur.execute(insert_sql, (
            pid,
            pname,
            raw,
            phone,
            rec,
            evidence
        ))

        count += 1

    if i % 5000 == 0:
        conn.commit()
        print("processed:", i)

conn.commit()

print("candidates found:", count)

sample = cur.execute("""

SELECT *
FROM unrecovered_appointment_candidates
LIMIT 20

""").fetchall()

print("SAMPLE")

for r in sample:
    print(tuple(r))

conn.close()
