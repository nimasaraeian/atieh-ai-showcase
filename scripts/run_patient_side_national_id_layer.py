import sqlite3

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"
TOTAL_PATIENTS = 140457

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def qident(x: str) -> str:
    return '"' + x.replace('"', '""') + '"'

def table_exists(name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def cols(table: str):
    cur.execute(f"PRAGMA table_info({qident(table)})")
    return [r[1] for r in cur.fetchall()]

def nonempty_nid_rows(table: str) -> int:
    cur.execute(f"""
        SELECT COUNT(*)
        FROM {qident(table)}
        WHERE patient_id IS NOT NULL
          AND national_id IS NOT NULL
          AND trim(CAST(national_id AS TEXT)) <> ''
    """)
    return cur.fetchone()[0] or 0

if not table_exists("patient_phone_recovered_v2"):
    raise SystemExit("ERROR: patient_phone_recovered_v2 not found")

if not table_exists("national_id_master_tiered"):
    raise SystemExit("ERROR: national_id_master_tiered not found")

candidates = []
for candidate in ["patients_national_id_clean", "patient_national_id_bridge_from_phone", "patients"]:
    if table_exists(candidate):
        c = cols(candidate)
        if "patient_id" in c and "national_id" in c:
            cnt = nonempty_nid_rows(candidate)
            candidates.append((candidate, cnt))

print("CANDIDATES:")
for name, cnt in candidates:
    print(f" - {name}: {cnt}")

nonzero = [x for x in candidates if x[1] > 0]
if nonzero:
    nonzero.sort(key=lambda x: (-x[1], x[0]))
    source_table = nonzero[0][0]
else:
    raise SystemExit("ERROR: no non-empty patient-side national-id source found")

for s in [
    "DROP TABLE IF EXISTS national_id_patient_side",
    "DROP TABLE IF EXISTS national_id_patient_side_tierA",
    "DROP TABLE IF EXISTS national_id_patient_side_increment",
    "DROP TABLE IF EXISTS national_id_patient_side_stats"
]:
    cur.execute(s)
conn.commit()

cur.execute(f"""
CREATE TABLE national_id_patient_side AS
SELECT DISTINCT
    patient_id,
    national_id
FROM {qident(source_table)}
WHERE patient_id IS NOT NULL
  AND national_id IS NOT NULL
  AND trim(CAST(national_id AS TEXT)) <> ''
""")
cur.execute("CREATE INDEX idx_nid_patient_side_pid ON national_id_patient_side(patient_id)")
cur.execute("CREATE INDEX idx_nid_patient_side_nid ON national_id_patient_side(national_id)")
conn.commit()

cur.execute("""
CREATE TABLE national_id_patient_side_tierA AS
SELECT DISTINCT
    p.patient_id,
    p.national_id
FROM national_id_patient_side p
JOIN national_id_master_tiered t
  ON t.national_id = p.national_id
WHERE t.identity_tier LIKE 'A%'
""")
cur.execute("CREATE INDEX idx_nid_patient_side_tierA_pid ON national_id_patient_side_tierA(patient_id)")
conn.commit()

cur.execute("""
CREATE TABLE national_id_patient_side_increment AS
SELECT DISTINCT
    p.patient_id,
    p.national_id,
    'patient_side_national_id_tierA' AS recovery_layer,
    0.97 AS confidence
FROM national_id_patient_side_tierA p
LEFT JOIN patient_phone_recovered_v2 b
  ON b.patient_id = p.patient_id
WHERE b.patient_id IS NULL
""")
cur.execute("CREATE INDEX idx_nid_patient_side_inc_pid ON national_id_patient_side_increment(patient_id)")
conn.commit()

cur.execute("SELECT COUNT(*) FROM national_id_patient_side")
all_links = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM national_id_patient_side_tierA")
tierA_links = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM national_id_patient_side_increment")
increment = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_phone_recovered_v2")
baseline = cur.fetchone()[0]

total_recovered = baseline + increment
coverage = round((total_recovered * 100.0) / TOTAL_PATIENTS, 2)

cur.execute("""
CREATE TABLE national_id_patient_side_stats AS
SELECT 'source_table' AS metric, ?
UNION ALL SELECT 'all_patient_nid_links', ?
UNION ALL SELECT 'tierA_patient_nid_links', ?
UNION ALL SELECT 'increment_patients', ?
UNION ALL SELECT 'baseline_patients', ?
UNION ALL SELECT 'total_recovered', ?
UNION ALL SELECT 'coverage', ?
""", (
    source_table,
    str(all_links),
    str(tierA_links),
    str(increment),
    str(baseline),
    str(total_recovered),
    str(coverage)
))
conn.commit()

print("")
print("=== PATIENT SIDE NATIONAL ID LAYER (FIXED SOURCE) ===")
print("source_table:", source_table)
print("all_links:", all_links)
print("tierA_links:", tierA_links)
print("increment:", increment)
print("baseline:", baseline)
print("total:", total_recovered)
print("coverage:", coverage)

conn.close()
