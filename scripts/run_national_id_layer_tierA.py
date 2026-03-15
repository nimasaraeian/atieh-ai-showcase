import sqlite3

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"
BASELINE_TARGET = 113318
TOTAL_PATIENTS = 140457

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def qident(x: str) -> str:
    return '"' + x.replace('"', '""') + '"'

def table_exists(name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def get_tables():
    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [r[0] for r in cur.fetchall()]

def get_cols(table: str):
    cur.execute(f"PRAGMA table_info({qident(table)})")
    return [r[1] for r in cur.fetchall()]

tables = get_tables()

if not table_exists("payments_national_id_map"):
    raise SystemExit("ERROR: payments_national_id_map not found")

if not table_exists("national_id_master_tiered"):
    raise SystemExit("ERROR: national_id_master_tiered not found")

baseline_candidates = []
for t in tables:
    cols = get_cols(t)
    if "patient_id" in cols:
        try:
            cur.execute(f"SELECT COUNT(DISTINCT patient_id) FROM {qident(t)}")
            cnt = cur.fetchone()[0] or 0
            if 50000 <= cnt <= TOTAL_PATIENTS:
                baseline_candidates.append((t, cnt, abs(cnt - BASELINE_TARGET)))
        except Exception:
            pass

if not baseline_candidates:
    raise SystemExit("ERROR: no baseline candidate table found")

baseline_candidates.sort(key=lambda x: (x[2], -x[1], x[0]))
baseline_table, baseline_count, _ = baseline_candidates[0]

bridge_tables = []
for t in tables:
    cols = get_cols(t)
    if "patient_id" in cols and "payment_id" in cols:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {qident(t)} WHERE patient_id IS NOT NULL AND payment_id IS NOT NULL")
            c = cur.fetchone()[0] or 0
            if c > 0:
                bridge_tables.append(t)
        except Exception:
            pass

if not bridge_tables:
    raise SystemExit("ERROR: no bridge table found")

tiered_cols = get_cols("national_id_master_tiered")
tier_col = None
for c in ["identity_tier", "tier", "tier_label", "segment_tier"]:
    if c in tiered_cols:
        tier_col = c
        break

if tier_col is None:
    raise SystemExit("ERROR: tier column not found")

# پاکسازی کامل
for s in [
    "DROP TABLE IF EXISTS national_id_layer_meta",
    "DROP TABLE IF EXISTS national_id_layer_baseline_patients",
    "DROP TABLE IF EXISTS national_id_layer_bridge_union",
    "DROP TABLE IF EXISTS national_id_layer_patient_nid",
    "DROP TABLE IF EXISTS national_id_layer_tierA_seed_nid",
    "DROP TABLE IF EXISTS national_id_layer_tierA_candidate_patients",
    "DROP TABLE IF EXISTS national_id_layer_tierA_increment",
    "DROP TABLE IF EXISTS national_id_layer_stats"
]:
    cur.execute(s)
conn.commit()

# meta
cur.execute("""
CREATE TABLE national_id_layer_meta (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

# baseline patients
cur.execute(f"""
CREATE TABLE national_id_layer_baseline_patients AS
SELECT DISTINCT patient_id
FROM {qident(baseline_table)}
WHERE patient_id IS NOT NULL
""")
cur.execute("CREATE INDEX idx_nid_layer_baseline_patient ON national_id_layer_baseline_patients(patient_id)")
conn.commit()

# bridge union
union_sql = "\nUNION\n".join(
    [f"SELECT DISTINCT patient_id, payment_id, {repr(t)} AS source_table FROM {qident(t)} WHERE patient_id IS NOT NULL AND payment_id IS NOT NULL"
     for t in bridge_tables]
)

cur.execute(f"""
CREATE TABLE national_id_layer_bridge_union AS
{union_sql}
""")
cur.execute("CREATE INDEX idx_nid_layer_bridge_patient ON national_id_layer_bridge_union(patient_id)")
cur.execute("CREATE INDEX idx_nid_layer_bridge_payment ON national_id_layer_bridge_union(payment_id)")
conn.commit()

# patient -> national_id
cur.execute("""
CREATE TABLE national_id_layer_patient_nid AS
SELECT DISTINCT
    b.patient_id,
    pnm.national_id,
    b.payment_id,
    b.source_table
FROM national_id_layer_bridge_union b
JOIN payments_national_id_map pnm
  ON pnm.payment_id = b.payment_id
WHERE pnm.national_id IS NOT NULL
""")
cur.execute("CREATE INDEX idx_nid_layer_patient_nid_patient ON national_id_layer_patient_nid(patient_id)")
cur.execute("CREATE INDEX idx_nid_layer_patient_nid_nid ON national_id_layer_patient_nid(national_id)")
conn.commit()

# Tier A seed
cur.execute(f"""
CREATE TABLE national_id_layer_tierA_seed_nid AS
SELECT DISTINCT pn.national_id
FROM national_id_layer_patient_nid pn
JOIN national_id_layer_baseline_patients bp
  ON bp.patient_id = pn.patient_id
JOIN national_id_master_tiered t
  ON t.national_id = pn.national_id
WHERE t.{qident(tier_col)} LIKE 'A%'
""")
cur.execute("CREATE INDEX idx_nid_layer_tierA_seed_nid ON national_id_layer_tierA_seed_nid(national_id)")
conn.commit()

# candidate patients
cur.execute("""
CREATE TABLE national_id_layer_tierA_candidate_patients AS
SELECT DISTINCT
    pn.patient_id,
    pn.national_id
FROM national_id_layer_patient_nid pn
JOIN national_id_layer_tierA_seed_nid s
  ON s.national_id = pn.national_id
""")
cur.execute("CREATE INDEX idx_nid_layer_tierA_candidate_patient ON national_id_layer_tierA_candidate_patients(patient_id)")
conn.commit()

# increment
cur.execute("""
CREATE TABLE national_id_layer_tierA_increment AS
SELECT DISTINCT
    c.patient_id,
    c.national_id,
    'national_id_tierA' AS recovery_layer,
    0.95 AS confidence
FROM national_id_layer_tierA_candidate_patients c
LEFT JOIN national_id_layer_baseline_patients b
  ON b.patient_id = c.patient_id
WHERE b.patient_id IS NULL
""")
cur.execute("CREATE INDEX idx_nid_layer_tierA_increment_patient ON national_id_layer_tierA_increment(patient_id)")
conn.commit()

# stats
cur.execute("SELECT COUNT(*) FROM national_id_layer_baseline_patients")
baseline_patients = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM national_id_layer_tierA_seed_nid")
seed_nids = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM national_id_layer_tierA_candidate_patients")
tierA_candidates = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM national_id_layer_tierA_increment")
tierA_increment = cur.fetchone()[0]

total_recovered = baseline_patients + tierA_increment
coverage = round((total_recovered * 100.0) / TOTAL_PATIENTS, 2)

cur.execute("""
CREATE TABLE national_id_layer_stats AS
SELECT 'baseline_table' AS metric, ? AS value
UNION ALL SELECT 'baseline_patients', ?
UNION ALL SELECT 'bridge_tables_count', ?
UNION ALL SELECT 'tier_column', ?
UNION ALL SELECT 'tierA_seed_national_ids', ?
UNION ALL SELECT 'tierA_candidate_patients', ?
UNION ALL SELECT 'tierA_increment_patients', ?
UNION ALL SELECT 'total_recovered_after_tierA', ?
UNION ALL SELECT 'coverage_after_tierA', ?
""", (
    baseline_table,
    str(baseline_patients),
    str(len(bridge_tables)),
    tier_col,
    str(seed_nids),
    str(tierA_candidates),
    str(tierA_increment),
    str(total_recovered),
    str(coverage),
))

meta = {
    "baseline_table": baseline_table,
    "baseline_count_detected": str(baseline_count),
    "tier_column": tier_col,
    "bridge_tables": ", ".join(bridge_tables),
}
for k, v in meta.items():
    cur.execute("INSERT INTO national_id_layer_meta(key, value) VALUES(?, ?)", (k, v))

conn.commit()

print("=== NATIONAL ID LAYER — TIER A (FIXED v2) ===")
print("baseline_table             :", baseline_table)
print("baseline_count_detected    :", baseline_count)
print("bridge_tables_count        :", len(bridge_tables))
print("tier_column                :", tier_col)
print("tierA_seed_national_ids    :", seed_nids)
print("tierA_candidate_patients   :", tierA_candidates)
print("tierA_increment_patients   :", tierA_increment)
print("total_recovered_after_A    :", total_recovered)
print("coverage_after_A           :", f"{coverage}%")

conn.close()
