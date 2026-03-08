import sqlite3, glob, sys

dbs = glob.glob("*.db")
if not dbs:
    print("NO_DB_FOUND")
    sys.exit(1)

db = dbs[0]
con = sqlite3.connect(db)
cur = con.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

print("DB:", db)
print("Tables:", len(tables))
print("Has stg_appointments:", ("stg_appointments" in tables))

if "stg_appointments" in tables:
    cnt = cur.execute("SELECT COUNT(1) FROM stg_appointments").fetchone()[0]
    err = cur.execute("SELECT COUNT(1) FROM stg_appointments WHERE parse_status='error'").fetchone()[0]
    print("stg_appointments count:", cnt)
    print("stg_appointments error:", err)
    print("error_rate:", (err / cnt if cnt else None))

con.close()
