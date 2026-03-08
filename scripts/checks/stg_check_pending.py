import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

print("pending_count =", cur.execute(
    "SELECT COUNT(1) FROM stg_appointments WHERE parse_status='pending'"
).fetchone()[0])

rows = cur.execute("""
SELECT id, file_name, sheet_name, row_number
FROM stg_appointments
WHERE parse_status='pending'
ORDER BY loaded_at ASC
LIMIT 20
""").fetchall()

print("\nPending rows:")
for r in rows:
    print(r)

c.close()