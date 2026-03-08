import sqlite3, os

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

# 1) detect date format by sampling
sample = cur.execute("SELECT appointment_date FROM appointments WHERE appointment_date IS NOT NULL LIMIT 50").fetchall()
sample_vals = [s[0] for s in sample if s and s[0] is not None]
print("SAMPLE appointment_date (first 10):", sample_vals[:10])

# 2) Try multiple patterns for Persian year 1404
patterns = ["1404/%", "1404-%", "1404%", "%/1404/%", "%1404%"]
counts = {}
for pat in patterns:
    counts[pat] = cur.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date LIKE ?", (pat,)).fetchone()[0]
print("PATTERN COUNTS:", counts)

# Pick the best pattern
best_pat = max(counts, key=counts.get)
best_count = counts[best_pat]
print("BEST_PATTERN:", best_pat, "=>", best_count)

if best_count == 0:
    print("No 1404-like pattern matched. appointment_date might be Gregorian or stored differently.")
else:
    appts_1404 = best_count
    # patient rows and unique patient names for that pattern
    patient_rows = cur.execute("""
        SELECT COUNT(*)
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        WHERE a.appointment_date LIKE ?
    """, (best_pat,)).fetchone()[0]
    unique_names = cur.execute("""
        SELECT COUNT(DISTINCT p.name)
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        WHERE a.appointment_date LIKE ?
    """, (best_pat,)).fetchone()[0]

    print("appointments_1404 =", appts_1404)
    print("patient_rows_1404 =", patient_rows)
    print("unique_patients_1404 =", unique_names)

conn.close()
