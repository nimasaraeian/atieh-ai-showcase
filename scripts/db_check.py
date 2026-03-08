import sqlite3

DB = "atieh_clinic.db"
c = sqlite3.connect(DB)
cur = c.cursor()

print("DB:", DB)

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("TABLES:", tables)

watch = ["patients","appointments","treatments","insurances","shifts","staging_rows","staging_appointments"]
for t in watch:
    if t in tables:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}_count:", n)
    else:
        print(f"{t}_count: MISSING")

if "appointments" in tables:
    sample = cur.execute("SELECT * FROM appointments LIMIT 5").fetchall()
    print("appointments_sample_5:", sample)

c.close()
