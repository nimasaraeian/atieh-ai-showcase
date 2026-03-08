import sqlite3, os

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

start = "2025-03-21"
end   = "2026-03-21"

rows = cur.execute("""
SELECT substr(date(appointment_date),1,7) AS ym, COUNT(*) c
FROM appointments
WHERE date(appointment_date) >= date(?) AND date(appointment_date) < date(?)
GROUP BY ym
ORDER BY ym
""", (start, end)).fetchall()

print("Year-Month counts (1404 window):")
for ym,c in rows:
    print(ym, c)

conn.close()
