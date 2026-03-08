import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(appointments)").fetchall()]
print("has_payment_type_raw =", "payment_type_raw" in cols)
print("has_payment_type_norm =", "payment_type_norm" in cols)

if "payment_type_norm" in cols:
    rows = cur.execute("""
    SELECT payment_type_norm, COUNT(1)
    FROM appointments
    GROUP BY payment_type_norm
    ORDER BY COUNT(1) DESC
    """).fetchall()
    print("payment_type_norm_distribution =", rows)

c.close()