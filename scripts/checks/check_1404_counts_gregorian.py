import sqlite3, os

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

# Persian year 1404 ~ 2025-03-21 to 2026-03-21 (exclusive)
start = "2025-03-21"
end   = "2026-03-21"

# Use SQLite date() to ignore time part (works with ISO 'YYYY-MM-DDTHH:MM:SS')
appts_1404 = cur.execute(
    "SELECT COUNT(*) FROM appointments WHERE date(appointment_date) >= date(?) AND date(appointment_date) < date(?)",
    (start, end)
).fetchone()[0]

unique_patients_1404 = cur.execute(
    """
    SELECT COUNT(DISTINCT p.name)
    FROM appointments a
    JOIN patients p ON p.id = a.patient_id
    WHERE date(a.appointment_date) >= date(?) AND date(a.appointment_date) < date(?)
    """,
    (start, end)
).fetchone()[0]

patient_rows_1404 = cur.execute(
    """
    SELECT COUNT(*)
    FROM appointments a
    JOIN patients p ON p.id = a.patient_id
    WHERE date(a.appointment_date) >= date(?) AND date(a.appointment_date) < date(?)
    """,
    (start, end)
).fetchone()[0]

print("RANGE_1404_GREGORIAN =", start, "to", end, "(end exclusive)")
print("appointments_1404 =", appts_1404)
print("patient_rows_1404 =", patient_rows_1404)
print("unique_patients_1404 =", unique_patients_1404)

conn.close()
