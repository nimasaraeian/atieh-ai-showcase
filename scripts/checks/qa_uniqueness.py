import sqlite3, os

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

distinct_name = cur.execute("SELECT COUNT(DISTINCT name) FROM patients WHERE name IS NOT NULL AND trim(name)<>''").fetchone()[0]

# name+phone distinct (only where both exist and phone not UNKNOWN)
distinct_name_phone = cur.execute("""
SELECT COUNT(DISTINCT name || '|' || phone)
FROM patients
WHERE name IS NOT NULL AND trim(name)<>'' 
  AND phone IS NOT NULL AND trim(phone)<>'' 
  AND phone NOT LIKE 'UNKNOWN_%'
""").fetchone()[0]

print("distinct_name =", distinct_name)
print("distinct_name_phone (phone valid-ish, not UNKNOWN) =", distinct_name_phone)

conn.close()
