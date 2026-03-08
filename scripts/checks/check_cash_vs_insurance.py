import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

print("\n=== Avg Priority by payment_type_norm ===")
rows = cur.execute("""
    SELECT payment_type_norm,
           ROUND(AVG(patient_priority_score), 2) AS avg_score,
           MIN(patient_priority_score) AS min_score,
           MAX(patient_priority_score) AS max_score,
           COUNT(*) AS cnt
    FROM appointments
    GROUP BY payment_type_norm
    ORDER BY cnt DESC
""").fetchall()

for r in rows:
    print(r)

print("\n=== Avg Priority by insurance_score (proxy for cash vs insurance) ===")
rows2 = cur.execute("""
    SELECT insurance_score,
           ROUND(AVG(patient_priority_score), 2) AS avg_score,
           COUNT(*) AS cnt
    FROM appointments
    GROUP BY insurance_score
    ORDER BY insurance_score DESC
""").fetchall()

for r in rows2:
    print(r)

c.close()