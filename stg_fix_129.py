import sqlite3

DB = "atieh_clinic.db"

c = sqlite3.connect(DB)
cur = c.cursor()

# 1) Count current target errors
count_before = cur.execute("""
SELECT COUNT(1)
FROM stg_appointments
WHERE parse_status='error'
  AND parse_error='Cannot create patient without name or phone'
""").fetchone()[0]
print("target_errors_before =", count_before)

# 2) Mark as skipped/quarantined
cur.execute("""
UPDATE stg_appointments
SET parse_status='skipped',
    parse_error='missing_identity'
WHERE parse_status='error'
  AND parse_error='Cannot create patient without name or phone'
""")
c.commit()
print("updated_rows =", cur.rowcount)

# 3) Verify after
count_after = cur.execute("""
SELECT COUNT(1)
FROM stg_appointments
WHERE parse_status='error'
""").fetchone()[0]
print("all_errors_after =", count_after)

# 4) Show status distribution
rows = cur.execute("""
SELECT parse_status, COUNT(1)
FROM stg_appointments
GROUP BY parse_status
ORDER BY COUNT(1) DESC
""").fetchall()
print("status_counts =", rows)

c.close()