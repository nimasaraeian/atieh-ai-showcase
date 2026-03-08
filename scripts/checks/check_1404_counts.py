import sqlite3, os

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

appointments_1404 = cur.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date LIKE '1404/%'").fetchone()[0]
unique_patients_1404 = cur.execute("""
    SELECT COUNT(DISTINCT p.name)
    FROM appointments a
    JOIN patients p ON p.id = a.patient_id
    WHERE a.appointment_date LIKE '1404/%'
""").fetchone()[0]

print("appointments_1404 =", appointments_1404)
print("unique_patients_1404 =", unique_patients_1404)

conn.close()
