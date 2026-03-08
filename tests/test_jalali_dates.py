import sqlite3, os

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

rows = cur.execute("""
SELECT appointment_date, appointment_date_jalali
FROM appointments
LIMIT 10
""").fetchall()

for r in rows:
    print(r)

conn.close()
