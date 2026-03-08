import sqlite3, os, re

db = os.path.abspath("atieh_clinic.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

total = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
null_phone = cur.execute("SELECT COUNT(*) FROM patients WHERE phone IS NULL OR trim(phone)=''").fetchone()[0]
unknown_phone = cur.execute("SELECT COUNT(*) FROM patients WHERE phone LIKE 'UNKNOWN_%'").fetchone()[0]

# phones that look like Iranian mobile (09xxxxxxxxx)
valid_iran = 0
rows = cur.execute("SELECT phone FROM patients WHERE phone IS NOT NULL").fetchall()
pat = re.compile(r"^09\d{9}$")
for (ph,) in rows:
    if ph and pat.match(ph.strip()):
        valid_iran += 1

print("patients_total =", total)
print("phone_null_or_empty =", null_phone)
print("phone_UNKNOWN =", unknown_phone)
print("phone_valid_iran_09xxxxxxxxx =", valid_iran)
print("valid_phone_percent =", round((valid_iran/total)*100,2) if total else None)

conn.close()
