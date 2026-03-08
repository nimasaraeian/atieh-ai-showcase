import sqlite3

DB = "atieh_clinic.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

rows = cur.execute("""
SELECT parse_error, COUNT(*) as cnt
FROM stg_appointments
WHERE parse_status='error'
GROUP BY parse_error
ORDER BY cnt DESC
LIMIT 15
""").fetchall()

print("TOP ERRORS:")
for err, cnt in rows:
    print(cnt, "x", err)

conn.close()
