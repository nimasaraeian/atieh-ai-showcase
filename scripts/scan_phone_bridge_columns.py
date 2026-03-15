import sqlite3

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def qident(x: str) -> str:
    return '"' + x.replace('"', '""') + '"'

def cols(table: str):
    cur.execute(f"PRAGMA table_info({qident(table)})")
    return [r[1] for r in cur.fetchall()]

targets = [
    "patients",
    "patient_phone_lookup",
    "patient_phone_map",
    "payments_clean",
    "payments_national_id_map",
    "payments_match_exact_phone",
    "payments_match_phone_last8_safe"
]

print("=== COLUMN SCAN ===")
for t in targets:
    try:
        c = cols(t)
        print(f"\n[{t}]")
        for x in c:
            print(" -", x)
    except Exception as e:
        print(f"\n[{t}] ERROR: {e}")

conn.close()
