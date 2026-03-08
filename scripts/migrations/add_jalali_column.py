import sqlite3, os

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("ALTER TABLE appointments ADD COLUMN appointment_date_jalali TEXT")

conn.commit()
conn.close()

print("Column appointment_date_jalali added.")
