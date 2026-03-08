import sqlite3, os
import jdatetime
from datetime import datetime

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

rows = cur.execute("SELECT id, appointment_date FROM appointments").fetchall()

for r in rows:
    id_, d = r
    if not d:
        continue

    g = datetime.fromisoformat(d.replace("T"," "))
    j = jdatetime.datetime.fromgregorian(datetime=g)

    jalali = f"{j.year}/{j.month:02}/{j.day:02}"

    cur.execute(
        "UPDATE appointments SET appointment_date_jalali=? WHERE id=?",
        (jalali,id_)
    )

conn.commit()
conn.close()

print("All dates converted to Jalali.")
