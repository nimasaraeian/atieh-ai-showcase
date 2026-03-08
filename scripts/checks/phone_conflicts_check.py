import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

# find duplicate phones in patients (if any)
rows = cur.execute("""
SELECT phone, COUNT(1) as cnt
FROM patients
WHERE phone IS NOT NULL AND TRIM(phone) <> ''
GROUP BY phone
HAVING cnt > 1
ORDER BY cnt DESC
LIMIT 20
""").fetchall()

print("duplicate_phones_top20 =", rows)
c.close()