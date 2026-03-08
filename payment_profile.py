import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(appointments)").fetchall()]
print("appointments_columns =", cols)

payment_col = None
for name in ["payment_type", "payment_method", "payment", "pay_type"]:
    if name in cols:
        payment_col = name
        break

print("appointments_payment_column =", payment_col)
if payment_col is None:
    c.close()
    raise SystemExit("No payment column found in appointments")

query = f"""
SELECT {payment_col}, COUNT(1)
FROM appointments
GROUP BY {payment_col}
ORDER BY COUNT(1) DESC
LIMIT 50
"""

rows = cur.execute(query).fetchall()
print("\nTop payment values:")
for v, cnt in rows:
    print(repr(v), cnt)

c.close()